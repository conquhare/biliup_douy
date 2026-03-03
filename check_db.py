# -*- coding: utf-8 -*-
import sqlite3
import json

conn = sqlite3.connect(r'e:\biliup_live_rec\biliup_code\data\data.sqlite3')
cursor = conn.cursor()

cursor.execute("SELECT id, template_name, title FROM uploadstreamers WHERE title = '' OR title IS NULL")
rows = cursor.fetchall()

print("=== Upload Templates with Empty Title ===")
for row in rows:
    id_, name, title = row
    print(f"ID {id_}: {name}")
    print(f"  title: '{title}' (empty or null)")

print("\n=== Problem Analysis ===")
print("When upload_config.title is Some(''):")
print("  1. recorder.filename_prefix = Some('')")
print("  2. filename_template() returns sanitize_filename('')")
print("  3. sanitize_filename('') returns '_'")
print("  4. Video title becomes '_' on Bilibili!")

conn.close()
