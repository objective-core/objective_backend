FROM postgis/postgis:14-3.3

ADD ./web/schema.sql /docker-entrypoint-initdb.d