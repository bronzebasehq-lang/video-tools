; SIVO-Remotion — one-click Windows installer (Phase 3).
; Built on Linux with makensis (NSIS 3.09). Target: Windows 10/11, SAC-on.
;
; Per-user install (no admin, no UAC prompt): %LOCALAPPDATA%\Programs\SIVO
; Python is installed silently into $INSTDIR\python by the bundled
; python.org installer (signed by Python Software Foundation).
; No terminal, no API keys, no downloads at install time.
;
; What the customer sees: 1 folder screen (default path, can change) ->
; install progress -> Finish (with "Run SIVO" checked by default).
; Desktop shortcut: SIVO -> pythonw.exe gui.py (no console window ever).

!include "MUI2.nsh"

Name "SIVO"
OutFile "build\SIVO-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\SIVO"
InstallDirRegKey HKCU "Software\SIVO" "InstallDir"
RequestExecutionLevel user
; Non-solid LZMA (default when /SOLID is omitted) with a 16 MB dictionary:
; the payload is ~745 MB and the build VM has ~2.7 GB free RAM — solid
; compression of the whole payload in one block crashed makensis (SIGBUS).
; Non-solid compresses each file separately, bounding peak memory.
; Output is slightly larger.
SetCompressor lzma
SetCompressorDictSize 16
XPStyle on

!define MUI_ABORTWARNING
; "Run SIVO" on the Finish page: the MUI macro's Exec quoting breaks when
; RUN contains quotes, so use a custom function (the macro Calls it).
!define MUI_FINISHPAGE_RUN $INSTDIR\python\pythonw.exe
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchSivo
!define MUI_FINISHPAGE_RUN_TEXT "Run SIVO"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Function LaunchSivo
  Exec '"$INSTDIR\python\pythonw.exe" "$INSTDIR\gui.py"'
FunctionEnd

Section "SIVO" SecMain
  SetOutPath "$INSTDIR"
  ; The payload/ dir is EXACTLY the ship set (assembled by the build step):
  ; app code + Windows node_modules + node + chrome + ffmpeg + memes.
  File /r "payload\*"

  ; Empty dir the app writes WAVs into (File /r does not create empty dirs).
  CreateDirectory "$INSTDIR\public\audio"

  ; Visual C++ runtime (node.exe links against VCRUNTIME140.dll; it is
  ; present on most Windows 10/11 machines, but a fresh machine may lack
  ; it). Microsoft-signed vc_redist installer, silent. Exit 0 = installed,
  ; 1638 = a newer version is already present, 3010 = restart needed
  ; (suppressed by /norestart). Any other code -> warn and CONTINUE (the
  ; runtime may still be present; a later failure will surface in the GUI
  ; with the real error instead of aborting the whole install here).
  DetailPrint "Installing Visual C++ runtime (one time, if needed)..."
  ExecWait '"$INSTDIR\vc-redist.exe" /install /quiet /norestart' $0
  ${If} $0 != 0
  ${AndIf} $0 != 1638
  ${AndIf} $0 != 3010
    MessageBox MB_OK|MB_ICONEXCLAMATION "Visual C++ runtime install returned code $0. SIVO will still try to continue — if the app fails to start, re-run this installer."
  ${EndIf}
  Delete "$INSTDIR\vc-redist.exe"

  ; Install Python 3.12 silently into $INSTDIR\python (per-user, no UAC).
  ; Include_tcltk=1 is REQUIRED (the GUI is tkinter). pip/test/docs/dev not
  ; needed. No .py association, no Start Menu entries from Python itself.
  ; The python.org installer is Authenticode-signed (Python Software
  ; Foundation); SmartScreen may still ask "Run anyway" for the SIVO
  ; installer itself (unsigned) — that is NORMAL, not a SAC fail (see
  ; TEST-SAC.md). The Python installer runs as a child process of the
  ; SIVO installer, with a hidden window.
  DetailPrint "Installing Python 3.12 (one time)..."
  ExecWait '"$INSTDIR\python-installer.exe" /quiet InstallAllUsers=0 TargetDir="$INSTDIR\python" PrependPath=0 Include_tcltk=1 Include_pip=0 Include_test=0 Include_doc=0 Include_dev=0 Include_debug=0 Include_launcher=0 InstallLauncherAllUsers=0 AssociateFiles=0 Shortcuts=0' $0
  ${If} $0 != 0
    MessageBox MB_OK|MB_ICONSTOP "Python install failed (exit code $0). SIVO cannot run without Python. Please re-run this installer. If the problem persists, send the installer log to support."
    Abort
  ${EndIf}
  ; The Python installer .exe (27 MB) is not needed after install.
  Delete "$INSTDIR\python-installer.exe"

  ; Desktop + Start Menu shortcuts -> pythonw.exe gui.py (no console).
  ; NSIS CreateShortCut has NO startdir parameter: the shortcut's
  ; "Start in" folder comes from the current $OUTDIR, which is $INSTDIR
  ; (SetOutPath at the top of this section). Icon defaults to the
  ; target exe (pythonw.exe) — no custom .ico in v1.
  CreateShortCut "$DESKTOP\SIVO.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\gui.py"'
  CreateDirectory "$SMPROGRAMS\SIVO"
  CreateShortCut "$SMPROGRAMS\SIVO\SIVO.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\gui.py"'
  CreateShortCut "$SMPROGRAMS\SIVO\Uninstall SIVO.lnk" "$INSTDIR\Uninstall.exe"

  ; Uninstaller + Add/Remove Programs entry (HKCU, per-user).
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\SIVO" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SIVO" "DisplayName" "SIVO — Script In, Video Out"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SIVO" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SIVO" "Publisher" "Bronze Base"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SIVO" "DisplayVersion" "1.0.0-remotion"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\SIVO.lnk"
  Delete "$SMPROGRAMS\SIVO\SIVO.lnk"
  Delete "$SMPROGRAMS\SIVO\Uninstall SIVO.lnk"
  RMDir "$SMPROGRAMS\SIVO"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SIVO"
  DeleteRegKey HKCU "Software\SIVO"
  RMDir /r "$INSTDIR"
SectionEnd
