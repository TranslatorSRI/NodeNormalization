# NodeNorm Data Loader

This directory holds a Dockerfile that we need to set up a Redis pipe
node on Kubernetes. It doesn't actually need very much, but putting it
in here allows us to automatically generate it through GitHub Actions
whenever there is a new NodeNorm release.

See https://github.com/helxplatform/translator-devops/pull/768 for
information on how this container will be used.
