# nn-loader

This is an attempt to streamline the NodeNorm Loader into a single Docker instance that can be used to
create Redis database backups of NodeNorm. By putting everything into a single Docker instance, I hope
to be able to speed up file retrieval and database communication, and also simplify what we need to
actually create here.

## nn-loader algorithm

This loader will work like this:
1. This directory contains a Dockerfile that creates a highly configurable nn-loader instance which creates all six Redis servers (therefore it will need a LOT of memory and disk storage).
2. This instance will include both the Node Norm loader from this repository, plus the Redis server, plus the code required to download all the Babel files and run them through the Node Norm loader. The hope is that the savings we get from the network transfer and the complexity of the previous loader (see below), combined with running this on a multi-core setup like Hatteras, will provide us with a simpler, faster and easier to debug system.
3. It will be set up so that it can be run on either Sterling or in Hatteras. Ideally, we will support both the previous NodeNorm loader algorithm (see below) as well as this new single-Docker setup.

## Previous loader

The [previous loader](https://github.com/helxplatform/translator-devops/tree/9696ab749b4318ae541ec73df28b368229d04e38/helm/node-normalization-loader) used a multi-step loading process:
1. We create six Redis databases as separate pods in Helm.
2. We create multiple jobs on Kubernetes. Every job creates a Pod that downloads one JSON file from the RENCI Stars server and loads it into the six databases simultaneously.
3. At this point the databases are loaded, and can be used to serve NodeNorm content.
4. Additionally, we can dump the databases to disk, creating backups that can be used to restart NodeNorm instances in the future.

### Downsides to the previous loader

1. Ideally, we would like to run this on Hatteras rather than Sterling -- Kubernetes is best intended for running services rather than 
2. Doing this load on ITRB is going to get increasingly slow as the Babel size increases. Being able to send them either the Redis dumps (and then load them using [RIOT](https://github.com/redis-developer/riot)) or writing the output in the [Redis protocol format](https://redis.io/docs/reference/protocol-spec/) should speed up this process.
