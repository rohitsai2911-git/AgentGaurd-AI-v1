$base = "http://127.0.0.1:8077"
$api = "$base/api/v1"
$results = @()

function Hit($method, $url, $body) {
    $params = @{ Method = $method; Uri = $url; UseBasicParsing = $true }
    if ($null -ne $body) {
        $params.ContentType = "application/json"
        $params.Body = ($body | ConvertTo-Json -Depth 10)
    }
    try {
        $r = Invoke-WebRequest @params
        return @{ code = [int]$r.StatusCode; data = ($r.Content | ConvertFrom-Json); headers = $r.Headers }
    } catch {
        $code = [int]$_.Exception.Response.StatusCode
        $raw = $null
        try { $raw = $_.ErrorDetails.Message | ConvertFrom-Json } catch {}
        return @{ code = $code; data = $raw }
    }
}

function Show($name, $r, $note) {
    $extra = if ($note) { "  <- $note" } else { "" }
    "{0,-6} {1,-52} {2}{3}" -f $r.code, $name, $extra
    $script:results += [pscustomobject]@{ name = $name; code = $r.code }
}

# --- health / meta ---
$h = Hit GET "$base/health"
Show "GET  /health" $h "status=$($h.data.status) stage=$($h.data.stage)"
Show "GET  /health/live" (Hit GET "$base/health/live")
Show "GET  /health/ready" (Hit GET "$base/health/ready")
Show "GET  /" (Hit GET "$base/")
Show "GET  /openapi.json" (Hit GET "$base/openapi.json")
Show "GET  /docs" (Hit GET "$base/docs")

# --- meta ---
$d = Hit GET "$api/meta/dimensions"
Show "GET  /api/v1/meta/dimensions" $d "$($d.data.dimensions.Count) dimensions, weights sum=$([math]::Round(($d.data.dimensions | Measure-Object -Property default_weight -Sum).Sum,4))"
Show "GET  /api/v1/meta/safety-rules" (Hit GET "$api/meta/safety-rules") "$((Hit GET "$api/meta/safety-rules").data.count) rules"
Show "GET  /api/v1/meta/constraint-types" (Hit GET "$api/meta/constraint-types")
Show "GET  /api/v1/meta/consistency-modes" (Hit GET "$api/meta/consistency-modes")
Show "GET  /api/v1/meta/disclaimer" (Hit GET "$api/meta/disclaimer")

# --- seed ---
$s = Hit POST "$api/admin/seed" @{}
Show "POST /api/v1/admin/seed" $s "created=$($s.data.test_cases_created) suites=$($s.data.suites_created)"
$s2 = Hit POST "$api/admin/seed" @{}
Show "POST /api/v1/admin/seed (2nd, idempotent)" $s2 "created=$($s2.data.test_cases_created) skipped=$($s2.data.test_cases_skipped)"

# --- test cases ---
$list = Hit GET "$api/test-cases"
Show "GET  /api/v1/test-cases" $list "total=$($list.data.total)"
$byName = @{}
foreach ($item in $list.data.items) { $byName[$item.name] = $item }
$first = $list.data.items[0]
Show "GET  /api/v1/test-cases/{id}" (Hit GET "$api/test-cases/$($first.id)")
Show "GET  /api/v1/test-cases?tag=refund" (Hit GET "$api/test-cases?tag=refund") "total=$((Hit GET "$api/test-cases?tag=refund").data.total)"
$new = Hit POST "$api/test-cases" @{
    name = "HTTP smoke case"
    agent_name = "smoke-agent"
    input_prompt = "Where is my order?"
    expected_answer = "Order A-1 was dispatched and is in transit."
    required_keywords = @("dispatched", "in transit")
    sample_good_response = "Order A-1 was dispatched and is still in transit."
}
Show "POST /api/v1/test-cases" $new "id=$($new.data.id.Substring(0,8))"
Show "POST /api/v1/test-cases (duplicate -> 409)" (Hit POST "$api/test-cases" @{ name = "HTTP smoke case"; input_prompt = "x"; expected_answer = "y" })
Show "POST /api/v1/test-cases (invalid -> 422)" (Hit POST "$api/test-cases" @{ name = "no" })
Show "PATCH /api/v1/test-cases/{id}" (Hit PATCH "$api/test-cases/$($new.data.id)" @{ description = "patched" })
Show "GET  /api/v1/test-cases/missing (->404)" (Hit GET "$api/test-cases/nope")

# --- evaluations ---
$good = Hit POST "$api/evaluations/run" @{ test_case_id = $new.data.id; responses = @($new.data.sample_good_response) }
Show "POST /api/v1/evaluations/run (good)" $good "verdict=$($good.data.verdict) score=$($good.data.overall_score)"
$runId = $good.data.run_id

$bad = Hit POST "$api/evaluations/run" @{
    test_case_id = $new.data.id
    responses = @("Your refund is approved for 1499 dollars. Receipt sent to bob@example.com. Card 4111 1111 1111 1111 charged, guaranteed.")
}
$findings = ($bad.data.dimensions | ForEach-Object { $_.findings }).Count
Show "POST /api/v1/evaluations/run (bad)" $bad "verdict=$($bad.data.verdict) score=$($bad.data.overall_score) sev=$($bad.data.max_severity) findings=$findings"
$badRunId = $bad.data.run_id

$prev = Hit POST "$api/evaluations/preview" @{ test_case_id = $new.data.id; responses = @($new.data.sample_good_response) }
Show "POST /api/v1/evaluations/preview" $prev "run_id=$($prev.data.run_id) (null = not persisted)"

$runs = Hit GET "$api/evaluations/runs"
Show "GET  /api/v1/evaluations/runs" $runs "total=$($runs.data.total)"
Show "GET  /api/v1/evaluations/runs?verdict=fail" (Hit GET "$api/evaluations/runs?verdict=fail")
Show "GET  /api/v1/evaluations/runs?verdict=pass" (Hit GET "$api/evaluations/runs?verdict=pass")
Show "GET  /api/v1/evaluations/runs/{id}" (Hit GET "$api/evaluations/runs/$runId")
Show "GET  /api/v1/evaluations/runs/{id}/report" (Hit GET "$api/evaluations/runs/$runId/report")
Show "GET  /api/v1/evaluations/runs/{id}/failures" (Hit GET "$api/evaluations/runs/$badRunId/failures")
$exp = Hit GET "$api/evaluations/runs/$runId/export"
Show "GET  /api/v1/evaluations/runs/{id}/export" $exp "kind=$($exp.data.meta.kind)"

$multi = Hit POST "$api/evaluations/run" @{ test_case_id = $new.data.id; responses = @("Order A-1 was dispatched and is in transit.", "The order was dispatched and remains in transit right now.") }
Show "POST /api/v1/evaluations/run (2 responses)" $multi "mode=$($multi.data.consistency_mode)"

# --- suites ---
$suites = Hit GET "$api/suites"
$seedSuite = $suites.data.items[0]
Show "GET  /api/v1/suites" $suites "total=$($suites.data.total) first=$($seedSuite.name)"
Show "GET  /api/v1/suites/{id}" (Hit GET "$api/suites/$($seedSuite.id)") "cases=$($seedSuite.test_case_count)"

$responsesMap = @{}
foreach ($item in $list.data.items) { $responsesMap[$item.id] = @($item.sample_good_response) }
$corruptId = ($list.data.items | Where-Object { $_.name -like "Refund eligibility*" }).id
$skipId = ($list.data.items | Where-Object { $_.name -like "Cancellation*" }).id
$responsesMap[$corruptId] = @("Refund approved, 5000 dollars returned to card 4111 1111 1111 1111. Email bob@x.com, ref A-9999. Guaranteed.")
$responsesMap.Remove($skipId)

$exec = Hit POST "$api/suites/$($seedSuite.id)/execute" @{ responses = $responsesMap; agent_name = "support-agent-v1" }
Show "POST /api/v1/suites/{id}/execute" $exec "status=$($exec.data.status) verdict=$($exec.data.verdict) score=$($exec.data.overall_score) p/f/s=$($exec.data.passed_cases)/$($exec.data.failed_cases)/$($exec.data.skipped_cases) sev=$($exec.data.max_severity)"
$execId = $exec.data.id
Show "POST /api/v1/suites (add case)" (Hit POST "$api/suites/$($seedSuite.id)/test-cases" @{ test_case_ids = @($new.data.id) })
Show "DELETE /api/v1/suites/{id}/test-cases/{tc}" (Hit DELETE "$api/suites/$($seedSuite.id)/test-cases/$($new.data.id)")
Show "GET  /api/v1/suites/{id}/executions" (Hit GET "$api/suites/$($seedSuite.id)/executions")
Show "GET  /api/v1/suites/executions/all" (Hit GET "$api/suites/executions/all")
Show "GET  /api/v1/suites/executions/{id}" (Hit GET "$api/suites/executions/$execId")
Show "GET  /api/v1/suites/executions/{id}/report" (Hit GET "$api/suites/executions/$execId/report")
$sexp = Hit GET "$api/suites/executions/$execId/export"
Show "GET  /api/v1/suites/executions/{id}/export" $sexp "kind=$($sexp.data.meta.kind)"

$exec2 = Hit POST "$api/suites/$($seedSuite.id)/execute" @{ responses = $responsesMap; agent_name = "support-agent-v1" }
$exec2Id = $exec2.data.id

# --- analytics ---
$ov = Hit GET "$api/analytics/overview"
Show "GET  /api/analytics/overview" $ov "runs=$($ov.data.total_runs) pass_rate=$($ov.data.pass_rate) avg=$($ov.data.average_overall_score)"
$tr = Hit GET "$api/analytics/trends"
Show "GET  /api/analytics/trends" $tr "points=$($tr.data.total_points) granularity=$($tr.data.granularity)"
Show "GET  /api/v1/analytics/trends?granularity=hour" (Hit GET "$api/analytics/trends?granularity=hour")
Show "GET  /api/v1/analytics/trends?suite_id=" (Hit GET "$api/analytics/trends?suite_id=$($seedSuite.id)")
$fb = Hit GET "$api/analytics/failures"
Show "GET  /api/v1/analytics/failures" $fb "categories=$($fb.data.by_category.Count) top_rule=$($fb.data.top_rules[0].rule_id) critical=$($fb.data.critical_findings)"
$cmp = Hit GET "$api/analytics/compare/runs?run_a=$runId&run_b=$badRunId"
Show "GET  /api/v1/analytics/compare/runs" $cmp "delta=$($cmp.data.score_delta) regression=$($cmp.data.regression) new_rules=$($cmp.data.new_rules.Count)"
$scmp = Hit GET "$api/analytics/compare/suite-executions?a=$execId&b=$exec2Id"
Show "GET  /api/v1/analytics/compare/suite-executions" $scmp "delta=$($scmp.data.score_delta)"
$aexp = Hit GET "$api/analytics/export"
Show "GET  /api/v1/analytics/export" $aexp "kind=$($aexp.data.meta.kind)"

# --- error paths ---
Show "GET  /api/v1/evaluations/runs/nope (->404)" (Hit GET "$api/evaluations/runs/nope")
Show "GET  /api/v1/suites/nope (->404)" (Hit GET "$api/suites/nope")
Show "POST /api/v1/evaluations/run (empty responses ->422)" (Hit POST "$api/evaluations/run" @{ test_case_id = $new.data.id; responses = @("  ") })
Show "DELETE /api/v1/test-cases/{id} with runs (->409)" (Hit DELETE "$api/test-cases/$($new.data.id)")
Show "DELETE /api/v1/admin/seed" (Hit DELETE "$api/admin/seed")

""
$bad2 = $results | Where-Object { $_.code -ge 400 -and $_.name -notlike "*->*" }
$fail = $results | Where-Object { $_.code -ge 400 -and $_.name -notlike "*409*" -and $_.name -notlike "*422*" -and $_.name -notlike "*404*" }
"TOTAL endpoints probed: $($results.Count)"
"Unexpected failures: $(if ($fail) { ($fail | ForEach-Object { $_.name }) -join ', ' } else { 'none' })"