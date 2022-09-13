# TimeTagger

*Tag your time, get the insight* - an open source time-tracker with an
interactive user experience and powerful reporting.

## Installing the Chart

To install the chart with the release name `my-release`:

```bash
helm repo add timetagger https://almarklein.github.io/timetagger
helm install my-release timetagger/timetagger
```

These commands deploy Wekan on the Kubernetes cluster in the default configuration.

Tip: List all releases using `helm list`

For all available values see `helm show values timetagger/timetagger`.

## Uninstalling the Chart

To uninstall/delete the my-release deployment:

```bash
helm delete my-release
```

The command removes all the Kubernetes components associated with the chart and
deletes the release.