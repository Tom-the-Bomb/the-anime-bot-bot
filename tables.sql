CREATE TABLE IF NOT EXISTS commandsusage(
command TEXT PRIMARY KEY,
usages BIGINT NOT NULL
)

CREATE TABLE IF NOT EXISTS emojioptions(
user_id BIGINT PRIMARY KEY,
enabled BOOLEAN NOT NULL
)

CREATE TABLE IF NOT EXISTS errors(
error_id serial,
error TEXT NOT NULL,
message TEXT NOT NULL,
created_at timestamp NOT NULL,
author_name TEXT NOT NULL,
command TEXT NOT NULL
)

CREATE TABLE IF NOT EXISTS logging(
guild_id BIGINT PRIMARY KEY, 
channel_id BIGINT NOT NULL, 
webhook TEXT NOT NULL, 
channel_create BOOLEAN NOT NULL, 
channel_update BOOLEAN NOT NULL, 
channel_delete BOOLEAN NOT NULL, 
role_create BOOLEAN NOT NULL, 
role_update BOOLEAN NOT NULL, 
role_delete BOOLEAN NOT NULL, 
guild_update BOOLEAN NOT NULL, 
emojis_update BOOLEAN NOT NULL, 
member_update BOOLEAN NOT NULL, 
member_ban BOOLEAN NOT NULL, 
member_unban BOOLEAN NOT NULL, 
invite_change BOOLEAN NOT NULL, 
member_join BOOLEAN NOT NULL, 
member_leave BOOLEAN NOT NULL, 
voice_channel_change BOOLEAN NOT NULL, 
message_delete BOOLEAN NOT NULL, 
message_edit BOOLEAN NOT NULL
)

CREATE TABLE IF NOT EXISTS prefix(
guild_id BIGINT PRIMARY KEY,
prefix VARCHAR[] NOT NULL
)

CREATE TABLE IF NOT EXISTS reactionrole(
guild_id BIGINT PRIMARY KEY,
message_id BIGINT NOT NULL,
roles JSON NOT NULL
)

CREATE TABLE IF NOT EXISTS socket(
name TEXT PRIMARY KEY,
count BIGINT NOT NULL
)

CREATE TABLE IF NOT EXISTS tags(
tag_name TEXT PRIMARY KEY,
tag_content TEXT NOT NULL,
author_id BIGINT NOT NULL,
message_id BIGINT NOT NULL,
uses BIGINT NOT NULL,
aliases TEXT []
)

CREATE TABLE IF NOT EXISTS todos(
)
