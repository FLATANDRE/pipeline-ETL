#!/bin/sh

if output=$(java -jar /deployments/polaris-admin-tool.jar "$@" 2>&1); then
    printf '%s\n' "$output"
    exit 0
else
    status=$?
fi

case "$output" in
    *"It appears this metastore manager has already been bootstrapped"*)
        printf '%s\n' "Polaris metastore is already initialized."
        exit 0
        ;;
    *)
        printf '%s\n' "$output" >&2
        exit "$status"
        ;;
esac
