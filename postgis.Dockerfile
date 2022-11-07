FROM postgis/postgis

ADD ./web/schema.sql /docker-entrypoint-initdb.d