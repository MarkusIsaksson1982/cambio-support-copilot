package org.cambio.ports;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.util.Iterator;

import static org.cambio.ports.Contracts.*;

public final class RoundTrip {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private RoundTrip() {}

    public static void main(String[] args) throws Exception {
        Path fixtures = Path.of(args.length == 0 ? "../fixtures" : args[0]);
        check(fixtures, "request.json", Request.class);
        check(fixtures, "masked_span.json", MaskedSpan.class);
        check(fixtures, "handoff_envelope.json", HandoffEnvelope.class);
        check(fixtures, "incident_report.json", IncidentReport.class);
        check(fixtures, "incident_result.json", IncidentResult.class);
        check(fixtures, "audit_events.json", AuditEvent[].class);
        System.out.println("Java fixture round trips passed.");
    }

    private static <T> void check(Path root, String name, Class<T> type) throws Exception {
        String source = java.nio.file.Files.readString(root.resolve(name));
        T value = MAPPER.readValue(source, type);
        JsonNode before = MAPPER.readTree(source);
        JsonNode after = MAPPER.readTree(MAPPER.writeValueAsString(value));
        if (!equivalent(before, after)) throw new IllegalStateException("Semantic JSON mismatch for " + name + ": " + after);
    }

    private static boolean equivalent(JsonNode a, JsonNode b) {
        if (a.isNumber() && b.isNumber()) return new BigDecimal(a.asText()).compareTo(new BigDecimal(b.asText())) == 0;
        if (a.isObject() && b.isObject()) {
            if (a.size() != b.size()) return false;
            Iterator<String> names = a.fieldNames();
            while (names.hasNext()) { String key = names.next(); if (!b.has(key) || !equivalent(a.get(key), b.get(key))) return false; }
            return true;
        }
        if (a.isArray() && b.isArray()) {
            if (a.size() != b.size()) return false;
            for (int i = 0; i < a.size(); i++) if (!equivalent(a.get(i), b.get(i))) return false;
            return true;
        }
        return a.equals(b);
    }
}
