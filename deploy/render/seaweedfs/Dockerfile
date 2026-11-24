# syntax=docker/dockerfile:1
#
# HIVE DOCS staging object storage on Render: SeaweedFS 4.54 as a PRIVATE service
# (docs/DEPLOYMENT_RENDER.md). Same image and digest as docker-compose.yml (V-07).
#
# Only the authenticated S3 API is reachable from the Render private network:
#   - master, volume and filer (HTTP and gRPC) bind to 127.0.0.1 (-ip, -ip.bind);
#   - the S3 gateway binds to 0.0.0.0 (-s3.ip.bind) on 8333; its gRPC port (18333) serves
#     only the IAM cache, which SeaweedFS 4.54 restricts to local callers;
#   - the Iceberg and Lance catalog listeners are disabled; the embedded IAM API is off;
#   - buckets are never auto-created; identities come from a Render secret file.
# A private service has no public URL. Nothing is copied from the build context: Render
# places secret files in the build context root, and .dockerignore excludes everything.
#
# The image's /entrypoint.sh is kept: it fixes /data ownership on the persistent disk, drops
# to the `seaweed` user (uid/gid 1000, which can read Render secret files) and adds
# -dir=/data -volume.max=0 -master.volumeSizeLimitMB=1024 to `server`.
FROM chrislusf/seaweedfs:4.54@sha256:4b42c212543a0acd4c0e675215ecdcaf62a186ef98def76c7e12701871222d15

EXPOSE 8333
CMD ["server", \
     "-ip=127.0.0.1", \
     "-ip.bind=127.0.0.1", \
     "-s3.ip.bind=0.0.0.0", \
     "-master.telemetry=false", \
     "-s3", \
     "-s3.port=8333", \
     "-s3.port.iceberg=0", \
     "-s3.port.lance=0", \
     "-s3.config=/etc/secrets/s3.json", \
     "-s3.autoCreateBucket=false", \
     "-s3.iam=false"]
