FROM alpine:latest
RUN apk add --no-cache git bash
WORKDIR /data

RUN git clone https://github.com/havelund/dejavu.git /tmp/dejavu_case_study && \
    cd /tmp/dejavu_case_study && \
    git checkout 2b5052d89e3a961de7344a2bdcb7adf1308f2bca

CMD mkdir -p data/ && \
    cp -r /tmp/dejavu_case_study/out/examples/* data/ && \
    find data/ -type d | while read dir; do \
      qtls=$(ls "$dir"/*.qtl 2>/dev/null); \
      csvs=$(ls "$dir"/*.csv 2>/dev/null); \
      if [ -n "$qtls" ] && [ -n "$csvs" ]; then \
        for csv in $csvs; do \
          for qtl in $qtls; do \
            echo "$dir/$(basename "$csv"), $dir/$(basename "$qtl")"; \
          done; \
        done; \
      fi; \
    done > instructions.txt