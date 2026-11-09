# C# port

.NET 8 records and `System.Text.Json` models are in `Cambio.Ports`. The console round-trip check reads the shared fixtures, deserializes each core type, serializes it again, and compares JSON trees semantically.

From this directory:

```sh
~/.dotnet/dotnet run --project Cambio.Ports.RoundTrip -- ../fixtures
```
