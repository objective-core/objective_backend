FROM postgis/postgis:15-3.3

ADD ./web/schema.sql /docker-entrypoint-initdb.d