#### Local Testing: creating Docker images
MPIC Coordinator
```bash
docker build -t mpiccoordinator . --build-arg SERVICE_PATH=src/mpic_coordinator_service --progress=plain
```
MPIC CAA Checker
```bash
docker build -t mpiccaachecker . --build-arg SERVICE_PATH=src/mpic_caa_checker_service --progress=plain
```
MPIC CAA Checker
```bash
docker build -t mpicdcvchecker . --build-arg SERVICE_PATH=src/mpic_dcv_checker_service --progress=plain
``` 

#### Local Testing: running Docker containers with Docker Compose
(See `/deployment-examples/local-docker-compose/README.md` for more information)
