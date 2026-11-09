using System.Text.Json;
using System.Text.Json.Serialization;

namespace Cambio.Ports;

public sealed record Request(
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("id")] string? Id);

public sealed record MaskedSpan(
    [property: JsonPropertyName("category")] string Category,
    [property: JsonPropertyName("start")] int Start,
    [property: JsonPropertyName("stop")] int Stop,
    [property: JsonPropertyName("replacement")] string Replacement);

public sealed record HandoffEnvelope(
    [property: JsonPropertyName("contract_version")] string ContractVersion,
    [property: JsonPropertyName("request_id")] string RequestId,
    [property: JsonPropertyName("request_type")] string RequestType,
    [property: JsonPropertyName("plugin_version")] string PluginVersion,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("handoff_reasons")] string[] HandoffReasons,
    [property: JsonPropertyName("route")] string Route,
    [property: JsonPropertyName("masked_text")] string MaskedText,
    [property: JsonPropertyName("masked_categories")] string[] MaskedCategories,
    [property: JsonPropertyName("rule")] JsonElement Rule,
    [property: JsonPropertyName("model")] JsonElement Model,
    [property: JsonPropertyName("output")] JsonElement Output);

public sealed class AuditEvent
{
    [JsonPropertyName("audit_version")] public string AuditVersion { get; init; } = "";
    [JsonPropertyName("ts")] public string Ts { get; init; } = "";
    [JsonPropertyName("event")] public string Event { get; init; } = "";
    [JsonPropertyName("request_id")] public string RequestId { get; init; } = "";
    [JsonExtensionData] public Dictionary<string, JsonElement>? Extra { get; init; }
}

public sealed record IncidentReport(
    [property: JsonPropertyName("schema_version")] string SchemaVersion,
    [property: JsonPropertyName("what")] string What,
    [property: JsonPropertyName("when")] string When,
    [property: JsonPropertyName("where")] string Where,
    [property: JsonPropertyName("harm")] string Harm,
    [property: JsonPropertyName("immediate_action")] string ImmediateAction,
    [property: JsonPropertyName("confidence")] double Confidence,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("route")] string? Route,
    [property: JsonPropertyName("source_request_id")] string? SourceRequestId);

public sealed record IncidentResult(
    [property: JsonPropertyName("report")] JsonElement Report,
    [property: JsonPropertyName("report_errors")] string[] ReportErrors,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("handoff_reasons")] string[] HandoffReasons);
