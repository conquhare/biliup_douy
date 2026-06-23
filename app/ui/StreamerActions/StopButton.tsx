import React from 'react';
import { useSWRConfig } from 'swr';
import useSWRMutation from 'swr/mutation';
import {Button, Popconfirm} from "@douyinfe/semi-ui";
import {IconClose} from "@douyinfe/semi-icons";
import {API_BASE, LiveStreamerEntity} from "@/app/lib/api-streamer";

interface StopButtonProps {
    streamer: LiveStreamerEntity;
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

const stopStreamer = async (url: string) => {
    const response = await fetch(API_BASE + url,
        {
            method: 'PUT',
        }
    );
    return response;
};

export const StopButton: React.FC<StopButtonProps> = ({
                                                          streamer,
                                                          onSuccess,
                                                          onError
                                                      }) => {
    const { mutate } = useSWRConfig();

    const { trigger: stopTrigger, isMutating } = useSWRMutation(
        `/v1/streamers/${streamer.id}/pause`,
        stopStreamer
    );

    const handleStop = async () => {
        try {
            await stopTrigger();
            await mutate('/v1/streamers');
            onSuccess?.();
        } catch (error) {
            console.error('停止失败:', error);
            onError?.(error as Error);
        }
    };

    return (
        <Popconfirm
            title="确定停止录制并提交投稿？"
            content="停止后将触发上传和投稿，是否继续？"
            onConfirm={handleStop}
        >
            <Button
                theme="borderless"
                icon={<IconClose />}
                loading={isMutating}
                disabled={streamer.status === 'Idle'}
                aria-label="停止"
            />
        </Popconfirm>
    );
};