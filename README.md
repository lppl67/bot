# Base

A simple docker stack that creates a Discord Bot


## Configuration

Create a file called `config.yaml` in the root of this repository with the following details:

```yaml
bot:
  command_prefix: !
  token: YOUR TOKEN HERE

logging:
  level: INFO

postgres:
  host: localhost
  port: 5432
  user: postgres
  database: postgres

categories:
  bal_update: 637285154846539776
  game_room: 637285252204855357

channels:
  archive: 653693819610726401
  rolls_history: 653693859703947320

roles:
  host: 637285473592672256
  cashier: 637283646713364490

maxes:
  637283588953341953: 100000000000000000
  637283980764512257: 1000000
  637284058833092628: 500000
  637284012884230192: 300000
  637284100612423704: 150000
  637284143998435351: 50000
  637284173647708172: 25000

flowers:
  red:
    url: https://runescape.wiki/images/6/6c/Red_flowers_detail.png
    value: hot
    emoji: <:redflower:505851036330885120>
  blue:
    url: https://runescape.wiki/images/d/d6/Blue_flowers_detail.png
    value: cold
    emoji: <:blueflower:505851036058124289>
  orange:
    url: https://runescape.wiki/images/9/99/Orange_flowers_detail.png
    value: hot
    emoji: <:orangeflower:505851036322496523>
  rainbow:
    url: https://runescape.wiki/images/f/fd/Flowers_%28mixed%29_detail.png
    value: none
    emoji: <:rainbowflower:505851036184084481>
  purple:
    url: https://runescape.wiki/images/3/3d/Purple_flowers_detail.png
    value: cold
    emoji: <:purpleflower:505851035932426251>
  yellow:
    url: https://runescape.wiki/images/a/a6/Yellow_flowers_detail.png
    value: hot
    emoji: <:yellowflower:505851036578086922>
  pastel:
    url: https://runescape.wiki/images/5/55/Flowers_%28pastel%29_detail.png
    value: cold
    emoji: <:pastelflower:505851036267708417>
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
