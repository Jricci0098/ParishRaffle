<#
.SYNOPSIS
    Populate a running Picnic Raffle Manager instance with a demo dataset:
    an event, 3 stations, 20 prizes, sample sales, and a few drawn/claimed winners.

.EXAMPLE
    ./deploy/seed-demo.ps1 -BaseUrl https://picnic-raffle-207884166310.us-central1.run.app -AdminPin 0068
#>
param(
    [Parameter(Mandatory = $true)][string]$BaseUrl,
    [Parameter(Mandatory = $true)][string]$AdminPin
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")
$admin = @{ "X-Admin-Pin" = $AdminPin }

function Post($path, $body, $headers = @{}) {
    return Invoke-RestMethod -Method Post -Uri "$BaseUrl$path" -Headers $headers `
        -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 6)
}

Write-Host "==> Creating event + 3 stations"
Post "/api/setup/wizard" @{
    event_name = "Saint Paul VI Parish Picnic Raffle 2026"
    sessions   = 2
    stations   = @(
        @{ name = "Ticket Table 1"; ticket_range_start = 5000; ticket_range_end = 5199; ticket_width = 6; active = $true },
        @{ name = "Ticket Table 2"; ticket_range_start = 5200; ticket_range_end = 5399; ticket_width = 6; active = $true },
        @{ name = "Ticket Table 3"; ticket_range_start = 5400; ticket_range_end = 5599; ticket_width = 6; active = $true }
    )
} $admin | Out-Null

Write-Host "==> Opening sales"
Post "/api/admin/sales/open" @{} $admin | Out-Null

Write-Host "==> Importing 20 prizes"
$names = @("Chocolate Basket","Restaurant Gift Card","School Backpack","Coffee Basket",
    "Wine Gift Set","Toy Bundle","Spa Day Package","Grocery Gift Card","Family Board Games",
    "Movie Night Basket","Gardening Kit","BBQ Grill Set","Bakery Gift Box","Bookstore Voucher",
    "Sports Equipment","Handmade Quilt","Electronics Bundle","Pizza Party","Ice Cream Basket","Local Honey Set")
$lines = @("prize_number,name,session,pickup_station")
for ($i = 1; $i -le 20; $i++) {
    $s = if ($i -gt 10) { 2 } else { 1 }
    $p = @("A", "B", "C")[($i - 1) % 3]
    $lines += "$i,$($names[$i-1]),$s,$p"
}
Post "/api/prizes/import" @{ content = ($lines -join "`n") } $admin | Out-Null

# Map stations by range so this works regardless of assigned ids.
$stations = Invoke-RestMethod "$BaseUrl/api/stations"
$s1 = ($stations | Where-Object { $_.ticket_range_start -eq 5000 }).id
$s2 = ($stations | Where-Object { $_.ticket_range_start -eq 5200 }).id
$s3 = ($stations | Where-Object { $_.ticket_range_start -eq 5400 }).id

function Sale($sid, $f, $l, $q) {
    Post "/api/sales" @{ station_id = $sid; first_name = $f; last_name = $l; quantity = $q } | Out-Null
}

Write-Host "==> Creating sample sales"
Sale $s1 "Mary" "Jones" 20      # 005000-005019
Sale $s1 "Robert" "Smith" 10    # 005020-005029
Sale $s1 "Susan" "Williams" 5   # 005030-005034
Sale $s2 "James" "Brown" 15     # 005200-005214
Sale $s2 "Patricia" "Davis" 8   # 005215-005222
Sale $s2 "Michael" "Miller" 20  # 005223-005242
Sale $s3 "Linda" "Wilson" 10    # 005400-005409
Sale $s3 "David" "Anderson" 25  # 005410-005434
Sale $s3 "Barbara" "Thomas" 5   # 005435-005439

# Map prize number -> id.
$prizes = Invoke-RestMethod "$BaseUrl/api/prizes"
$byNum = @{}; foreach ($p in $prizes) { $byNum[$p.prize_number] = $p.id }

function Draw($num, $ticket) {
    Post "/api/draws" @{ prize_id = $byNum[$num]; ticket_number = $ticket } | Out-Null
}
function Claim($num) {
    Post "/api/prizes/$($byNum[$num])/claim" @{ verified_by = "volunteer" } | Out-Null
}

Write-Host "==> Drawing 6 winners (3 claimed, 3 left unclaimed)"
Draw 1 "005005"; Draw 2 "005025"; Draw 3 "005032"
Draw 4 "005205"; Draw 5 "005410"; Draw 6 "005436"
Claim 1; Claim 2; Claim 3

Write-Host ""
Write-Host "Done. Open these in your browser:"
Write-Host "  $BaseUrl/display   (TV board - 3 claimed, 3 unclaimed)"
Write-Host "  $BaseUrl/drawing   (advances to Prize #7)"
Write-Host "  $BaseUrl/pickup    (search 005205 or a name)"
Write-Host "  $BaseUrl/admin     (PIN $AdminPin)"
