# Java port

Java 21 records and Jackson models are in this Maven project. The round-trip main reads the shared fixtures, deserializes each core type, serializes it again, and compares JSON values semantically.

From this directory:

```sh
JAVA_HOME="$HOME/jdk" PATH="$HOME/jdk/bin:$PATH" "$HOME/maven/bin/mvn" compile exec:java
```
