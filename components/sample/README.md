# sample-java

`sample-java` is a minimal Maven module for the research polyglot monorepo. It
is intentionally separate from the Bazel C++ slice so development workflows, CI
target selection, dependency management, and test reporting can model multiple
build systems.

Run it from this directory:

```sh
mvn test
mvn package
```

The module targets Java 17 and uses JUnit 5 for tests.
