package org.cambio.ports;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.LinkedHashMap;
import java.util.Map;

public final class Contracts {
    private Contracts() {}

    public record Request(@JsonProperty("type") String type,
                          @JsonProperty("text") String text,
                          @JsonProperty("id") String id) {}

    public record MaskedSpan(@JsonProperty("category") String category,
                             @JsonProperty("start") int start,
                             @JsonProperty("stop") int stop,
                             @JsonProperty("replacement") String replacement) {}

    public record HandoffEnvelope(@JsonProperty("contract_version") String contractVersion,
            @JsonProperty("request_id") String requestId,
            @JsonProperty("request_type") String requestType,
            @JsonProperty("plugin_version") String pluginVersion,
            @JsonProperty("status") String status,
            @JsonProperty("handoff_reasons") String[] handoffReasons,
            @JsonProperty("route") String route,
            @JsonProperty("masked_text") String maskedText,
            @JsonProperty("masked_categories") String[] maskedCategories,
            @JsonProperty("rule") JsonNode rule,
            @JsonProperty("model") JsonNode model,
            @JsonProperty("output") JsonNode output) {}

    public static final class AuditEvent {
        @JsonProperty("audit_version") public String auditVersion;
        @JsonProperty("ts") public String ts;
        @JsonProperty("event") public String event;
        @JsonProperty("request_id") public String requestId;
        private final Map<String, JsonNode> extra = new LinkedHashMap<>();
        @JsonAnySetter public void add(String key, JsonNode value) { extra.put(key, value); }
        @JsonAnyGetter public Map<String, JsonNode> extra() { return extra; }
    }

    public record IncidentReport(@JsonProperty("schema_version") String schemaVersion,
            @JsonProperty("what") String what, @JsonProperty("when") String when,
            @JsonProperty("where") String where, @JsonProperty("harm") String harm,
            @JsonProperty("immediate_action") String immediateAction,
            @JsonProperty("confidence") double confidence, @JsonProperty("status") String status,
            @JsonProperty("route") String route, @JsonProperty("source_request_id") String sourceRequestId) {}

    public record IncidentResult(@JsonProperty("report") JsonNode report,
            @JsonProperty("report_errors") String[] reportErrors, @JsonProperty("status") String status,
            @JsonProperty("handoff_reasons") String[] handoffReasons) {}
}
