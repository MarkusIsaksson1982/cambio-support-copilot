#!/usr/bin/env bash
# Round-trip every shared fixture through each language port. Skips missing toolchains.
set -u; cd "$(dirname "$0")"; rc=0
export PATH="$HOME/.dotnet:$HOME/jdk/bin:$HOME/maven/bin:$PATH" DOTNET_CLI_TELEMETRY_OPTOUT=1
[ -d "$HOME/jdk" ] && export JAVA_HOME="$HOME/jdk"
python3 -m pytest -q ../tests/test_ports_fixtures.py || rc=1
if command -v dotnet >/dev/null; then (cd csharp && dotnet run --project Cambio.Ports.RoundTrip -- ../fixtures) || rc=1; else echo "skip C#: no dotnet"; fi
if command -v mvn >/dev/null && command -v java >/dev/null; then (cd java && mvn -q compile exec:java) || rc=1; else echo "skip Java: no jdk/maven"; fi
if command -v npm >/dev/null; then (cd typescript && { [ -d node_modules ] || npm install --silent; } && npm test --silent) || rc=1; else echo "skip TS: no node"; fi
exit $rc
