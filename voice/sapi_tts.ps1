# SIVO - sapi_tts.ps1 : Windows SAPI text-to-speech + word boundaries.
#
# Uses System.Speech (.NET Framework, Microsoft-signed) - SAC-safe.
# No third-party DLLs, no downloads, no model files.
#
# MUST run under Windows PowerShell 5.1 (powershell.exe), NOT PowerShell 7
# (pwsh), because System.Speech is .NET Framework only.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File voice\sapi_tts.ps1 `
#     -TextFile sentence.txt -OutWav out.wav -OutJson out.json `
#     [-Voice "Microsoft Zira Desktop"] [-Rate 0] [-Ssml]
#
# Output:
#   OutWav  - 22050 Hz, 16-bit, mono WAV
#   OutJson - {"words": [{"w": "word", "s": start_sec, "e": end_sec}],
#              "timing": "bookmarks"|"progress", "n_words": N}
#             "timing" tells the caller WHICH event source produced the
#             boundaries (v2.3: assemble.py logs it loudly — Minh's 17/10
#             test had karaoke out of sync with the voice and the log said
#             nothing about whether bookmarks fired or fallback was used).
#             Times are relative to the start of this sentence.
#
# Two modes:
# - Plain (default): SpeakProgress events (CharacterPosition/CharacterCount
#   slice the exact substring), so karaoke timing is exact with no speech
#   recognition.
# - SSML (-Ssml, v2.2 prosody variants): the input is SSML with <prosody>
#   + <mark name="wN"/> before each word. Word timings come from
#   BookmarkReached events (mark name -> word index). SpeakProgress is NOT
#   used here — its positions point into the SSML markup, not the words.
#   In SSML mode -Rate is ignored (SSML <prosody rate> is authoritative).
#   If no bookmarks fire, Words is empty and the Python caller falls back
#   to estimated word times (graceful, never a crash).

param(
    [Parameter(Mandatory = $true)][string]$TextFile,
    [Parameter(Mandatory = $true)][string]$OutWav,
    [Parameter(Mandatory = $true)][string]$OutJson,
    [string]$Voice = "",
    [int]$Rate = 0,
    [switch]$Ssml
)

$ErrorActionPreference = "Stop"  # any error terminates with non-zero exit

$Text = Get-Content -Raw -Encoding UTF8 $TextFile
if ($null -eq $Text) { $Text = "" }

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
if ($Voice -ne "") {
    $found = $false
    foreach ($v in $synth.GetInstalledVoices()) {
        if ($v.VoiceInfo.Name -eq $Voice) { $synth.SelectVoice($Voice); $found = $true; break }
    }
    if (-not $found) { Write-Warning "SAPI voice '$Voice' not found, using default voice." }
}
$synth.Rate = 0
if (-not $Ssml) { $synth.Rate = $Rate }

# Event handlers run in their own scope: keep shared state in script scope.
$script:SpeakText = $Text
$script:Words = New-Object System.Collections.ArrayList
if ($Ssml) {
    # Recover the spoken tokens: strip SSML tags, unescape entities, split
    # on whitespace. Mark w{i} maps to tokens[i] (assemble.py emits one
    # <mark> per whitespace token, in order).
    $plain = $Text -replace '<[^>]+>', ''
    $plain = $plain.Replace('&apos;', "'").Replace('&quot;', '"').Replace('&gt;', '>').Replace('&lt;', '<').Replace('&amp;', '&')
    $script:Tokens = @($plain -split '\s+' | Where-Object { $_ -ne '' })
    $synth.add_BookmarkReached({
        param($sender, $e)
        if ($e.Bookmark -match '^w(\d+)$') {
            $idx = [int]$Matches[1]
            if ($idx -lt $script:Tokens.Count) {
                [void]$script:Words.Add([PSCustomObject]@{
                    w = $script:Tokens[$idx]
                    s = [Math]::Round($e.AudioPosition.TotalSeconds, 3)
                    e = 0.0
                })
            }
        }
    })
} else {
    $synth.add_SpeakProgress({
        param($sender, $e)
        $w = $script:SpeakText.Substring($e.CharacterPosition, $e.CharacterCount).Trim()
        if ($w -ne "") {
            [void]$script:Words.Add([PSCustomObject]@{
                w = $w
                s = [Math]::Round($e.AudioPosition.TotalSeconds, 3)
                e = 0.0
            })
        }
    })
}
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$synth.SetOutputToWaveFile($OutWav, $format)
if ($Ssml) {
    $synth.SpeakSsml($Text)
} else {
    $synth.Speak($Text)
}
$synth.SetOutputToNull()

# End times: next word's start; last word's end = audio duration.
# WAV is 22050 Hz 16-bit mono: duration = (bytes - 44 header) / (22050 * 2).
if ($script:Words.Count -gt 0) {
    $wavBytes = (Get-Item $OutWav).Length - 44
    $duration = [Math]::Round($wavBytes / (22050 * 2), 3)
    for ($i = 0; $i -lt $script:Words.Count; $i++) {
        if ($i + 1 -lt $script:Words.Count) { $script:Words[$i].e = $script:Words[$i + 1].s }
        else { $script:Words[$i].e = $duration }
    }
}
# Write JSON WITHOUT a UTF-8 BOM: PowerShell 5.1 Set-Content -Encoding UTF8
# writes a BOM, and Python's plain json.load() chokes on it (Minh hit this
# 17/10: "Unexpected UTF-8 BOM"). WriteAllText with UTF8Encoding($false)
# writes pure UTF-8, no BOM. (build_props.py also reads with utf-8-sig now,
# so old BOM files still parse — belt and suspenders.)
$JsonText = @{ words = @($script:Words); timing = $(if ($Ssml) { "bookmarks" } else { "progress" }); n_words = $script:Words.Count } | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($OutJson, $JsonText, (New-Object System.Text.UTF8Encoding($false)))
