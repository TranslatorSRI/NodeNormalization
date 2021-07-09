
from dataclasses import dataclass, field
from rediscluster import RedisCluster
import aioredis
from typing import List, Dict


@dataclass
class Resource:
    host_name: str
    port: str = "6379"


@dataclass
class RedisInstance:
    ssl_enabled: bool = False
    password: str = ''
    is_cluster: bool = True
    hosts: List[Resource] = field(default_factory=list)
    host: Resource = None  # Use if is_cluster == False
    db: int = None  # if instance is not a cluster it supports multiple dbs

    def __post_init__(self):
        if len(self.hosts):
            self.hosts = [Resource(**host) if isinstance(host, dict) else host for host in self.hosts]
        if self.host and isinstance(self.host, dict):
            self.host = Resource(**self.host)


@dataclass
class ConnectionConfig:
    eq_id_to_id_db: RedisInstance
    id_to_data_db: RedisInstance
    curie_to_bl_type_db: RedisInstance

    def __post_init__(self):
        # Converts inner data dicts to dataclasses
        if isinstance(self.curie_to_bl_type_db, dict):
            self.curie_to_bl_type_db = RedisInstance(**self.curie_to_bl_type_db)
        if isinstance(self.id_to_data_db, dict):
            self.id_to_data_db = RedisInstance(**self.id_to_data_db)
        if isinstance(self.eq_id_to_id_db, dict):
            self.eq_id_to_id_db = RedisInstance(**self.eq_id_to_id_db)


class RedisConnection:
    """
    Abstraction layer for redis interaction.
    Supporting both Clustered, standalone redis backends.
    """
    def __init__(self):
        self.connector = None

    @classmethod
    async def create(cls, redis_instance: RedisInstance):
        """
        Create redis connection.
        """
        self = RedisConnection()
        other_params = {}
        if redis_instance.password:
            other_params['password'] = redis_instance.password
        if redis_instance.ssl_enabled:
            other_params['ssl'] = redis_instance.ssl_enabled

        if redis_instance.is_cluster:
            host: Resource
            hosts = [{"host": host.host_name, "port": host.port} for host in redis_instance.hosts]
            other_params = {}
            if redis_instance.ssl_enabled:
                other_params['ssl_cert_reqs'] = False

            redis_connector = RedisCluster(startup_nodes=hosts,
                                           decode_responses=True,
                                           skip_full_coverage_check=True,
                                           password=redis_instance.password, **other_params)
        else:
            host: Resource = redis_instance.host
            redis_connector = await aioredis.create_redis_pool(f'redis://{host.host_name}:{host.port}',
                                                               db=redis_instance.db,
                                                               **other_params)

        self.connector = redis_connector
        return self

    async def mget(self, *keys, encoding='utf-8'):
        """
        Execute mget command.
        """
        if isinstance(self.connector, RedisCluster):
            self.connector: RedisCluster
            return self.connector.mget(keys=keys)
        elif isinstance(self.connector, aioredis.commands.Redis):
            self.connector: aioredis.commands.Redis
            return await self.connector.mget(*keys, encoding=encoding)

    async def get(self, key, encoding='utf-8'):
        """
        Execute redis get command.
        """
        if isinstance(self.connector, RedisCluster):
            self.connector: RedisCluster
            return self.connector.get(name=key)
        elif isinstance(self.connector, aioredis.commands.Redis):
            self.connector: aioredis.commands.Redis
            return await self.connector.get(key, encoding=encoding)

    def close(self):
        """
        Close underlying connection.
        """
        self.connector.close()

    async def wait_closed(self):
        """
        Wait for closed underlying connection.
        """
        if isinstance(self.connector, RedisCluster):
            self.connector: RedisCluster
            if self.connector.connection:
                self.connector.close()
        elif isinstance(self.connector, aioredis.commands.Redis):
            self.connector: aioredis.commands.Redis
            await self.connector.wait_closed()

    async def lrange(self, key, start, stop, encoding='utf-8'):
        """
        Execute Lrange command.
        """
        if isinstance(self.connector, RedisCluster):
            self.connector: RedisCluster
            return self.connector.lrange(name=key, start=start, end=stop)
        elif isinstance(self.connector, aioredis.commands.Redis):
            self.connector:  aioredis.commands.Redis
            return await self.connector.lrange(key=key, start=start, stop=stop, encoding=encoding)

    def pipeline(self):
        return self.connector.pipeline()


class RedisConnectionFactory:
    """
    Class to create three redis connections based on config
    """
    connections: Dict[str, RedisConnection] = {}

    ID_TO_ID_DB_CONNECTION_NAME = 'id_to_id'
    ID_TO_NODE_DATA_DB_CONNECTION_NAME = 'id_to_node'
    CURIE_PREFIX_TO_BL_TYPE_DB_CONNECTION_NAME = 'curie_to_bl'

    def __init__(self):
        pass

    @staticmethod
    def get_config(file_name) -> ConnectionConfig:
        import yaml
        with open(file_name) as f:
            config = ConnectionConfig(**yaml.load(f, yaml.FullLoader))
        return config

    @classmethod
    async def create_connection_pool(cls, config_file_path):
        config = RedisConnectionFactory.get_config(config_file_path)
        self = RedisConnectionFactory()
        if not RedisConnectionFactory.connections:
            RedisConnectionFactory.connections = {
                RedisConnectionFactory.ID_TO_ID_DB_CONNECTION_NAME: await RedisConnection.create(config.eq_id_to_id_db),
                RedisConnectionFactory.ID_TO_NODE_DATA_DB_CONNECTION_NAME: await RedisConnection.create(config.id_to_data_db),
                RedisConnectionFactory.CURIE_PREFIX_TO_BL_TYPE_DB_CONNECTION_NAME: await RedisConnection.create(config.curie_to_bl_type_db)
            }
        return self

    @staticmethod
    def get_connection(connection_id):
        return RedisConnectionFactory.connections[connection_id]


if __name__== '__main__':
    ips = ["10.233.91.90","10.233.73.195","10.233.80.110"]
    startup = [
        {"host": "127.0.0.1", "port": "6379"},
        {"host": "127.0.0.1", "port": "6380"},
        {"host": "127.0.0.1", "port": "6381"},
    ]
    host_port_remap = [
    {'from_host': ips[0], 'from_port': 6379, 'to_host': '127.0.0.1', 'to_port': 6379},
    {'from_host': ips[1], 'from_port': 6379, 'to_host': '127.0.0.1', 'to_port': 6380},
    {'from_host': ips[2], 'from_port': 6379, 'to_host': '127.0.0.1', 'to_port': 6381}
        ]
    rc = RedisCluster(
        startup_nodes=startup,
        host_port_remap=host_port_remap,
        decode_responses=True)
    print(rc.connection_pool.nodes.nodes)
    print(rc.ping())
    print(rc.set('foo', 'bar'))
    print(rc.get('foo'))
