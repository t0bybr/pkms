FROM alpine:3.20
RUN apk add --no-cache restic bash coreutils tzdata
ENV RESTIC_REPO=/backups/pkms \
    RESTIC_PASSWORD=change_me \
    RESTIC_INCLUDE_DATA=/data \
    RESTIC_INCLUDE_INDEX=/index
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
