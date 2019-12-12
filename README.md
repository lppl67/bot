# Base

A simple docker stack that creates a Discord Bot


## Configuration

Create a file called `config.yaml` in the root of this repository with the following details:

```yaml
bot:
  command_prefix: "!"
  token: TOKEN

logging:
  level: INFO

postgres:
  host: db
  port: 5432
  user: postgres
  database: postgres
```

You can provide a `password` in the `postgres` section. If you don't provide it, the container checks the POSTGRES_PASSWORD
envvar. This lets you specify everything just once if you use the Postgres database container as well.

You should make a `.env` file with the following contents:

```ini
POSTGRES_PASSWORD=your Postgres password here 
```

## Running

1. Change directory to the root of the repository
1. Run the following commands:
    1. `sudo wget -qO - http://get.docker.com | sh`
    1. `sudo apt install docker-compose`
    1. `sudo systemctl enable docker`
    1. `sudo systemctl start docker`
    1. `sudo usermod -aG docker $(whoami)`
    1. `logout`
    1. `docker-compose up`

## Debugging with Postgres

If you wish to add PGAdmin4 to the stack to explore the database, you can easily amend the compose script with the following service:

```yaml
  pga4:
     
    image: thajeztah/pgadmin4
    restart: always
    depends_on:
      - db
    links:
      - db
    ports:
      - 5050:5050

```

If you are using an ARM device like a Raspberry Pi, use `simonqbs/arm-pgadmin4` as the image instead, keep everything else the same. 

When PGAdmin4 fires up, browse to `http://your-machine:5050` and add a server for the `db_1` host.
