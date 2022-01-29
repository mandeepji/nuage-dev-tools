# API Spec Development Utility Tools

## spec-tool

Contains:

### idea plugin

intellij plugin to get notified spec diff (Entity & spec) while developing feature.

Copy spec-tool/idea-plugin/vsd-spec-plugin-*.zip into your intellij plugin folder and restart intellij.

Step 1: open plugin and set api specification dir
Step 2: when you save entity after code change, pluing will notify about diff in spec.

### command line tool

command line script available for running and finding diff between entity & spec.

```
spec-util/run.sh -s <API Spec File/Dir> -e <Entity Java File/Dir>
```

