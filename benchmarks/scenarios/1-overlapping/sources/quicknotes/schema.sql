create table notes (id integer primary key autoincrement, title text not null, body text not null, created_at timestamp not null);
create table tags (id integer primary key autoincrement, name text not null unique);
create table note_tags (note_id integer references notes(id) on delete cascade, tag_id integer references tags(id) on delete cascade);
