use crate::server::common::download::DownloaderMessage;
use crate::server::common::util::Recorder;
use crate::server::core::plugin::{DownloadPlugin, StreamStatus};
use crate::server::infrastructure::connection_pool::ConnectionPool;
use crate::server::infrastructure::context::{Context, PluginContext, Stage, Worker, WorkerStatus};
use crate::server::infrastructure::models::StreamerInfo;
use async_channel::Sender;
use ormlite::Model;
use ormlite::model::ModelBuilder;
use std::collections::hash_map::Entry;
use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, RwLock};
use std::time::Duration;
use tokio::sync::oneshot;
use tokio::task::JoinHandle;
use tracing::{debug, error, info, trace, warn};

/// ���䴦����
/// �������ֱ�����״̬�Ͳ���
#[derive(Debug)]
pub struct Monitor {
    /// ��Ϣ������
    sender: tokio::sync::mpsc::Sender<ActorMessage>,
    /// Actor������
    pool: ConnectionPool,
    /// ������Ϣ������
    down_sender: Sender<DownloaderMessage>,
    monitors: RwLock<HashMap<String, JoinHandle<()>>>,
}

impl Drop for Monitor {
    /// ���������ʱ�������߼�
    fn drop(&mut self) {
        let sender = self.sender.clone();
        tokio::spawn(async move {
            let msg = ActorMessage::Shutdown;
            let _ = sender.send(msg).await;
            info!("RoomsHandle killed")
        });
        // ��ֹ�������
        // self.kill.abort();
        // self.rooms_handle.kill.abort();
    }
}

impl Monitor {
    /// �����µķ��䴦����ʵ��
    ///
    /// # ����
    /// * `name` - ƽ̨����
    pub fn new(down_sender: Sender<DownloaderMessage>, pool: ConnectionPool) -> Self {
        // ������Ϣͨ��
        let (sender, receiver) = tokio::sync::mpsc::channel(1);
        let mut actor = RoomsActor::new(receiver);
        // ����Actor����
        let _kill = tokio::spawn(async move { actor.run().await });

        Self {
            sender,
            pool,
            down_sender,
            monitors: Default::default(),
        }
    }

    /// �����ͻ��˼��ѭ��
    ///
    /// # ����
    /// * `rooms_handle` - ���䴦����
    /// * `plugin` - ���ز��
    /// * `actor_handle` - Actor������
    /// * `interval` - ��ؼ�����룩
    pub(crate) async fn start_monitor(
        self: &Arc<Self>,
        platform_name: &str,
        plugin: Arc<dyn DownloadPlugin + Send + Sync>,
    ) {
        info!("start -> [{platform_name}]");
        // ��ȡƽ̨�����ѭ��������״λ�ȡ����Ĭ��ֵ��
        let platform_interval = self
            .get_first_room_config(platform_name)
            .await
            .map(|c| c.event_loop_interval)
            .unwrap_or(30);

        // ��ȡ��һ��Ҫ���ķ���
        while let Some(room) = self.next(platform_name).await {
            // ����״̬Ϊ�ȴ���
            room.change_status(Stage::Download, WorkerStatus::Pending)
                .await;
            let url = room.get_streamer().url.clone();
            let config = room.get_config();
            // ʹ�� checker_sleep ��Ϊ��������������������������ʹ�� event_loop_interval
            let check_interval = if config.checker_sleep > 0 {
                config.checker_sleep
            } else {
                config.event_loop_interval
            };
            let mut ctx = PluginContext::new(room.clone(), self.pool.clone());
            // ���ֱ��״̬
            let mut downloader = plugin.create_downloader(&mut ctx);
            match downloader.check_stream().await {
                Ok(StreamStatus::Live { mut stream_info }) => {
                    let sql_no_id = &stream_info.streamer_info;
                    let insert = match StreamerInfo::builder()
                        .url(sql_no_id.url.clone())
                        .name(room.live_streamer.remark.clone())
                        .title(sql_no_id.title.clone())
                        .date(sql_no_id.date)
                        .live_cover_path(sql_no_id.live_cover_path.clone())
                        .insert(ctx.pool())
                        .await
                    {
                        Ok(insert) => insert,
                        Err(e) => {
                            error!(e=?e, "�������ݿ�ʧ��");
                            continue;
                        }
                    };
                    info!(url = url, "room: is live -> ������");

                    // �޸� ctx
                    // stream_info.streamer_info = insert;
                    let context = ctx.to_context(insert.id, *stream_info);
                    // context
                    // *ctx.mut_stream_info_ext() = *stream_info;

                    // �������ؿ�ʼ��Ϣ
                    if self
                        .down_sender
                        .send(DownloaderMessage::Start(downloader, context))
                        .await
                        .is_ok()
                    {
                        info!("�ɹ���ʼ¼�� {}", url)
                    }
                }
                Ok(StreamStatus::Offline) => {
                    self.wake_waker(room.id()).await;
                    debug!(url = ctx.live_streamer().url, "δ����")
                }
                Err(e) => {
                    self.wake_waker(room.id()).await;
                    error!(e=?e, ctx=ctx.live_streamer().url,"���ֱ�������")
                }
            };
            // �ȴ���һ�μ�飨ʹ�õ��������������
            tokio::time::sleep(Duration::from_secs(check_interval)).await;
        }
        info!("exit -> [{platform_name}]")
    }

    /// ��ȡ��һ����������ã����ڻ�ȡƽ̨Ĭ�����ã�
    async fn get_first_room_config(&self, platform_name: &str) -> Option<crate::server::config::Config> {
        let workers = self.get_all().await;
        for worker in workers {
            // �򵥷��ص�һ���ҵ��ķ��������
            return Some(worker.get_config());
        }
        None
    }

    /// ���ӹ������������б�
    ///
    /// # ����
    /// * `worker` - Ҫ���ӵĹ�����
    pub async fn add(
        self: &Arc<Self>,
        worker: Arc<Worker>,
    ) -> Option<Arc<dyn DownloadPlugin + Send + Sync>> {
        let (send, recv) = oneshot::channel();
        let msg = ActorMessage::Add(send, worker.clone());
        let _ = self.sender.send(msg).await;
        let plugin = recv.await.expect("Actor task has been killed")?;

        self.rooms_handle_pool(plugin.clone());
        Some(plugin)
    }

    /// ���ӹ������������б�
    ///
    /// # ����
    /// * `worker` - Ҫ���ӵĹ�����
    pub async fn add_plugin(&self, plugin: Arc<dyn DownloadPlugin + Send + Sync>) {
        let (send, recv) = oneshot::channel();
        let msg = ActorMessage::AddPlugin(send, plugin);
        let _ = self.sender.send(msg).await;
        recv.await.expect("Actor task has been killed")
    }

    /// ɾ��ָ��ID�Ĺ�����
    ///
    /// # ����
    /// * `id` - Ҫɾ���Ĺ�����ID
    ///
    /// # ����
    /// ����ʣ�๤��������
    pub async fn del(&self, id: i64) {
        let (send, recv) = oneshot::channel();
        let msg = ActorMessage::Del {
            respond_to: send,
            id,
        };

        // ���Է��ʹ����������ʧ�ܣ������recv.awaitҲ��ʧ��
        // û�б�Ҫ�������ʧ��
        let _ = self.sender.send(msg).await;
        if let Some(worker) = recv.await.expect("Actor task has been killed") {
            worker
                .change_status(Stage::Download, WorkerStatus::Idle)
                .await;
        }
    }

    /// ɾ��ָ��ID�Ĺ�����
    ///
    /// # ����
    /// * `id` - Ҫɾ���Ĺ�����ID
    ///
    /// # ����
    /// ����ʣ�๤��������
    pub async fn get_worker(&self, id: i64) -> Option<Arc<Worker>> {
        let (send, recv) = oneshot::channel();
        let msg = ActorMessage::GetWorker {
            respond_to: send,
            id,
        };

        // ���Է��ʹ����������ʧ�ܣ������recv.awaitҲ��ʧ��
        // û�б�Ҫ�������ʧ��
        let _ = self.sender.send(msg).await;
        recv.await.expect("Actor task has been killed")
    }

    /// ɾ��ָ��ID�Ĺ�����
    ///
    /// # ����
    /// * `id` - Ҫɾ���Ĺ�����ID
    ///
    /// # ����
    /// ����ʣ�๤��������
    pub async fn get_all(&self) -> Vec<Arc<Worker>> {
        let (send, recv) = oneshot::channel();
        let msg = ActorMessage::GetAll { respond_to: send };

        // ���Է��ʹ����������ʧ�ܣ������recv.awaitҲ��ʧ��
        // û�б�Ҫ�������ʧ��
        let _ = self.sender.send(msg).await;
        recv.await.expect("Actor task has been killed")
    }

    /// ��ȡ��һ��Ҫ�����Ĺ�����
    ///
    /// # ����
    /// ������һ�������������û���򷵻�None
    async fn next(self: &Arc<Self>, platform_name: &str) -> Option<Arc<Worker>> {
        let (send, recv) = oneshot::channel();
        let msg = ActorMessage::NextRoom {
            respond_to: send,
            platform_name: platform_name.to_owned(),
        };

        // ���Է��ʹ����������ʧ�ܣ������recv.awaitҲ��ʧ��
        // û�б�Ҫ�������ʧ��
        let _ = self.sender.send(msg).await;
        recv.await.expect("Actor task has been killed")
    }

    /// �Żع�������
    ///
    /// # ����
    /// * `worker` - Ҫ�л��Ĺ�����
    pub async fn wake_waker(
        self: &Arc<Self>,
        id: i64,
    ) -> Option<Arc<dyn DownloadPlugin + Send + Sync>> {
        let (send, recv) = oneshot::channel();

        let msg = ActorMessage::WakeWaker(send, id);

        // ���Է��ʹ���
        let _ = self.sender.send(msg).await;
        let plugin = recv.await.expect("Actor task has been killed")?;
        self.rooms_handle_pool(plugin.clone());
        Some(plugin)
    }

    /// �Ƴ���������
    ///
    /// # ����
    /// * `worker` - Ҫ�л��Ĺ�����
    pub async fn make_waker(&self, id: i64) {
        let (send, recv) = oneshot::channel();

        let msg = ActorMessage::MakeWaker(send, id);

        // ���Է��ʹ���
        let _ = self.sender.send(msg).await;
        recv.await.expect("Actor task has been killed")
    }

    fn spawn_monitor_task(
        this: Arc<Self>,
        plugin: Arc<dyn DownloadPlugin + Send + Sync>,
        platform_name: String,
    ) -> JoinHandle<()> {
        tokio::spawn(async move {
            this.start_monitor(&platform_name, plugin).await;
        })
    }

    fn rooms_handle_pool(self: &Arc<Self>, plugin: Arc<dyn DownloadPlugin + Send + Sync>) {
        let platform_name = plugin.name().to_owned();
        match self.monitors.write().unwrap().entry(platform_name.clone()) {
            Entry::Occupied(mut entry) => {
                // �Ѿ���һ�������ˣ�����Ƿ����
                if entry.get().is_finished() {
                    // �������Ѿ����������� spawn һ��
                    let handle = Self::spawn_monitor_task(
                        Arc::clone(self),
                        plugin.clone(),
                        platform_name.clone(),
                    );
                    entry.insert(handle); // �滻�ɵ� JoinHandle
                } else {
                    // �������ܣ������κ���
                }
            }
            Entry::Vacant(entry) => {
                // û���������� spawn
                let handle = Self::spawn_monitor_task(
                    Arc::clone(self),
                    plugin.clone(),
                    platform_name.clone(),
                );
                entry.insert(handle);
            }
        }
    }
}

/// Actor��Ϣö��
/// ����RoomsActor���Դ�������Ϣ����
enum ActorMessage {
    /// ��ȡ��һ������
    NextRoom {
        respond_to: oneshot::Sender<Option<Arc<Worker>>>,
        platform_name: String,
    },
    /// ���ӹ�����
    Add(
        oneshot::Sender<Option<Arc<dyn DownloadPlugin + Send + Sync>>>,
        Arc<Worker>,
    ),
    /// ���ӹ�����
    AddPlugin(oneshot::Sender<()>, Arc<dyn DownloadPlugin + Send + Sync>),
    /// ɾ��������
    Del {
        respond_to: oneshot::Sender<Option<Arc<Worker>>>,
        id: i64,
    },
    /// ����
    GetWorker {
        respond_to: oneshot::Sender<Option<Arc<Worker>>>,
        id: i64,
    },
    /// ��������
    GetAll {
        respond_to: oneshot::Sender<Vec<Arc<Worker>>>,
    },
    /// ����ƽ̨
    GetPlatform {
        respond_to: oneshot::Sender<Vec<Arc<Worker>>>,
        platform_name: String,
    },
    /// �Żع�������
    WakeWaker(
        oneshot::Sender<Option<Arc<dyn DownloadPlugin + Send + Sync>>>,
        i64,
    ),
    /// �Ƴ���������
    MakeWaker(oneshot::Sender<()>, i64),
    Shutdown,
}

/// ����Actor
/// ���������б����ڲ�Actor
/// ƽ̨����
//     name: String,
struct RoomsActor {
    /// ��Ϣ������
    receiver: tokio::sync::mpsc::Receiver<ActorMessage>,
    /// ��Ծ�����б�
    platforms: HashMap<String, VecDeque<Arc<Worker>>>,
    /// ��ǰ����
    /// �ȴ������б�
    all_workers: Vec<Arc<Worker>>,
    // index: usize,
    // rooms: Vec<Arc<Worker>>,
    // waiting: Vec<Arc<Worker>>,
    /// ���ز��
    plugins: Vec<Arc<dyn DownloadPlugin + Send + Sync>>,
}

impl RoomsActor {
    /// �����µķ���Actorʵ��
    fn new(receiver: tokio::sync::mpsc::Receiver<ActorMessage>) -> Self {
        Self {
            receiver,
            // index: 0,
            platforms: Default::default(),
            all_workers: Default::default(),
            plugins: Vec::new(),
        }
    }

    /// ����Actor��ѭ��
    /// �������յ�����Ϣ
    async fn run(&mut self) {
        while let Some(msg) = self.receiver.recv().await {
            match msg {
                ActorMessage::NextRoom {
                    respond_to,
                    platform_name,
                } => {
                    // `let _ =` ���Է���ʱ���κδ���
                    // ���ʹ��`select!`��ȡ���ȴ���Ӧ�����ܻᷢ���������
                    let _ = respond_to.send(self.next(&platform_name));
                }
                ActorMessage::Add(respond_to, worker) => {
                    let plugin = self.add(worker);
                    let _ = respond_to.send(plugin);
                }
                ActorMessage::Del { respond_to, id } => {
                    // `let _ =` ���Է���ʱ���κδ���
                    // ���ʹ��`select!`��ȡ���ȴ���Ӧ�����ܻᷢ���������

                    let _ = respond_to.send(self.del(id).await);
                }
                ActorMessage::WakeWaker(sender, id) => {
                    // `let _ =` ���Է���ʱ���κδ���
                    let _ = sender.send(self.push_back(id));
                }
                ActorMessage::Shutdown => {
                    return;
                }
                ActorMessage::GetWorker { respond_to, id } => {
                    let option = self.get_worker(id);
                    // `let _ =` ���Է���ʱ���κδ���
                    let _ = respond_to.send(option);
                }
                ActorMessage::GetAll { respond_to } => {
                    // `let _ =` ���Է���ʱ���κδ���
                    let _ = respond_to.send(self.get_all());
                }

                ActorMessage::GetPlatform {
                    respond_to,
                    platform_name,
                } => {
                    // `let _ =` ���Է���ʱ���κδ���
                    let _ = respond_to.send(self.get_by_platform(&platform_name));
                }
                ActorMessage::MakeWaker(respond_to, id) => {
                    self.pop(id);
                    // `let _ =` ���Է���ʱ���κδ���
                    let _ = respond_to.send(());
                }
                ActorMessage::AddPlugin(respond_to, plugin) => {
                    self.add_plugin(plugin);
                    // `let _ =` ���Է���ʱ���κδ���
                    let _ = respond_to.send(());
                }
            }
        }
        info!("Rooms actor terminated");
    }

    fn add(&mut self, worker: Arc<Worker>) -> Option<Arc<dyn DownloadPlugin + Send + Sync>> {
        let plugin = self.matches(&worker.live_streamer.url)?;
        let platform_name = plugin.name().to_owned();
        self.all_workers.push(worker.clone());

        match self.platforms.entry(platform_name) {
            Entry::Occupied(mut entry) => {
                entry.get_mut().push_back(worker.clone());
                // entry.remove(); // ����ɾ��
            }
            Entry::Vacant(entry) => {
                entry.insert(VecDeque::from([worker.clone()])); // ������ֵ
            }
        }
        debug!("Added room [{}]", worker.live_streamer.url);
        Some(plugin)
    }

    fn add_plugin(&mut self, plugin: Arc<dyn DownloadPlugin + Send + Sync>) {
        self.plugins.push(plugin);
        debug!("Added plugin size[{}]", self.plugins.len());
    }

    fn get_worker(&mut self, id: i64) -> Option<Arc<Worker>> {
        self.all_workers
            .iter()
            .find(|worker| worker.id() == id)
            .cloned()
    }

    fn get_by_platform(&mut self, platform_name: &str) -> Vec<Arc<Worker>> {
        reuse_vec_arc(
            &mut self
                .platforms
                .get(platform_name)
                .unwrap_or(&VecDeque::new())
                .iter(),
        )
    }

    fn get_all(&mut self) -> Vec<Arc<Worker>> {
        reuse_vec_arc(&mut self.all_workers.iter())
    }

    /// ��ȡ��һ����������ѭ��������
    fn next(&mut self, platform_name: &str) -> Option<Arc<Worker>> {
        // ����ڲ�Vec�ǿյģ�������������Ȼ��ѭ�������������ռ����޷������κ�ֵ��
        let arc = self.platforms.get_mut(platform_name)?.pop_front()?;

        *arc.downloader_status.write().unwrap() = WorkerStatus::Pending;

        Some(arc)
    }

    /// �Żع�������
    fn push_back(&mut self, id: i64) -> Option<Arc<dyn DownloadPlugin + Send + Sync>> {
        // �����������Ҳ�����˵���÷����ѱ��Ƴ�����Ҳ���Ż�
        let worker = self.get_worker(id)?;
        
        // ��鵱ǰ״̬
        let current_status = worker.downloader_status.read().unwrap().clone();
        
        // �����ǰ��Working״̬��˵����������������
        // ��ʱ��Ӧ�÷Żض��У��ȴ�����������ɺ��ٵ��� push_back
        if matches!(current_status, WorkerStatus::Working(_)) {
            warn!("Room [{}] is still working, deferring push_back", worker.live_streamer.url);
            return None;
        }
        
        if let WorkerStatus::Pause = current_status {
            // ��ͣ״̬�򲻷Ż�
            warn!("Paused room [{}]", worker.live_streamer.url);
            return None;
        }
        for (name, queue) in self.platforms.iter_mut() {
            if queue.iter().any(|w| w.id() == id) {
                // ˵���ҵ����Ѿ���ӵķ��䣬���Ǹ��µ����
                warn!(name = name, "�����Ѹ����������");
                return None;
            }
        }

        let plugin = self.matches(&worker.live_streamer.url)?;
        self.platforms
            .get_mut(plugin.name())?
            .push_back(worker.clone());
        // ֱ������״̬ΪIdle����Ϊ��ʱӦ���Ѿ�����Working״̬��
        *worker.downloader_status.write().unwrap() = WorkerStatus::Idle;
        info!("Room [{}] status changed to Idle", worker.live_streamer.url);
        Some(plugin)
    }

    /// �Ƴ���������
    fn pop(&mut self, id: i64) {
        for (_name, queue) in self.platforms.iter_mut() {
            if let Some(pos) = queue.iter().position(|w| w.id() == id) {
                queue.remove(pos); // ֻɾ����������е�һ��ƥ��� worker
                return;
            }
        }
        warn!("�Ƴ��������� failed: No room found with id {}", id);
    }

    /// ɾ��ָ��ID�Ĺ�����
    async fn del(&mut self, id: i64) -> Option<Arc<Worker>> {
        let worker = self.get_worker(id)?;
        let plugin = self.matches(&worker.live_streamer.url)?;
        let platform_name = plugin.name();
        // �� platforms ��ɾ��
        if let Some(workers) = self.platforms.get_mut(platform_name) {
            workers.retain(|w| w.id() != id);
        } else {
            error!("Removed room [{:?}] {}", platform_name, id);
        }

        // �� all_workers ��ɾ��
        self.all_workers.retain(|w| w.id() != id);

        debug!("del worker size[{}]", self.all_workers.len());
        Some(worker)
    }

    /// ���URL�Ƿ�ƥ������ع������Ĳ��
    ///
    /// # ����
    /// * `url` - Ҫ����URL
    ///
    /// # ����
    /// ���URLƥ�䷵��true�����򷵻�false
    pub fn matches(&self, url: &str) -> Option<Arc<dyn DownloadPlugin + Send + Sync>> {
        for plugin in &self.plugins {
            trace!(
                platform_name = plugin.name(),
                url = url,
                "Found plugin for URL"
            );
            if plugin.matches(url) {
                return Some(plugin.clone());
            }
        }
        None
    }
}

fn reuse_vec_arc<'a, T: 'a, U: Iterator<Item = &'a Arc<T>>>(v: &mut U) -> Vec<Arc<T>> {
    v.into_iter().cloned().collect()
}

