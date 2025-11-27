### Build the image
```
docker build -t <image>:<tag> -f ./docker/Dockerfile .
```

### Run the image
 - Edit the docker/docker-compose.yaml file and set the image name based on the build above.
 - Copy the env.example to env and fill it with real data

```
docker compose -f docker/docker-compose.yaml up
```

The downloaded files will be available in the ebook folder
