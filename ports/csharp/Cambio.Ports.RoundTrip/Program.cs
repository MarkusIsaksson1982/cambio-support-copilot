using System.Text.Json;
using Cambio.Ports;

var root = Path.GetFullPath(args.Length > 0 ? args[0] : "../../fixtures");
var opts = new JsonSerializerOptions { PropertyNameCaseInsensitive = false, WriteIndented = true };
Check<Request>("request.json");
Check<MaskedSpan>("masked_span.json");
Check<HandoffEnvelope>("handoff_envelope.json");
Check<IncidentReport>("incident_report.json");
Check<IncidentResult>("incident_result.json");
Check<AuditEvent[]>("audit_events.json");
Console.WriteLine("C# fixture round trips passed.");

void Check<T>(string file)
{
    var source = File.ReadAllText(Path.Combine(root, file));
    var value = JsonSerializer.Deserialize<T>(source, opts) ?? throw new Exception($"Could not deserialize {file}");
    var roundTrip = JsonSerializer.Serialize(value, opts);
    using var before = JsonDocument.Parse(source);
    using var after = JsonDocument.Parse(roundTrip);
    if (!Equivalent(before.RootElement, after.RootElement))
        throw new Exception($"Semantic JSON mismatch for {file}:\n{roundTrip}");
}

static bool Equivalent(JsonElement a, JsonElement b)
{
    if (a.ValueKind != b.ValueKind)
    {
        if (a.ValueKind == JsonValueKind.Number && b.ValueKind == JsonValueKind.Number)
            return a.GetDouble() == b.GetDouble();
        return false;
    }
    return a.ValueKind switch
    {
        JsonValueKind.Object => a.EnumerateObject().Count() == b.EnumerateObject().Count() &&
            a.EnumerateObject().All(p => b.TryGetProperty(p.Name, out var v) && Equivalent(p.Value, v)),
        JsonValueKind.Array => a.GetArrayLength() == b.GetArrayLength() && a.EnumerateArray().Zip(b.EnumerateArray()).All(p => Equivalent(p.First, p.Second)),
        JsonValueKind.Number => a.GetDouble() == b.GetDouble(),
        JsonValueKind.String => a.GetString() == b.GetString(),
        JsonValueKind.True or JsonValueKind.False => a.GetBoolean() == b.GetBoolean(),
        JsonValueKind.Null => true,
        _ => false
    };
}
