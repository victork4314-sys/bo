!include "MUI2.nsh"

!define APP_NAME "Bio Speak"
!define COMPANY_NAME "Bio Speak"
!ifdef OUTPUT_DIR
!define BUILD_OUTPUT "${OUTPUT_DIR}"
!else
!define BUILD_OUTPUT "dist"
!endif
!ifdef PAYLOAD_DIR
!define PAYLOAD_ROOT "${PAYLOAD_DIR}"
!else
!define PAYLOAD_ROOT "build\\windows\\payload"
!endif

Name "${APP_NAME}"
OutFile "${BUILD_OUTPUT}\\BioSpeakInstaller.exe"
InstallDir "$PROGRAMFILES\\Bio Speak"
InstallDirRegKey HKCU "Software\\BioSpeak" "Install_Dir"
RequestExecutionLevel user

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"
    File /r "${PAYLOAD_ROOT}\\*.*"

    WriteUninstaller "$INSTDIR\\Uninstall.exe"

    CreateDirectory "$SMPROGRAMS\\Bio Speak"
    CreateShortCut "$SMPROGRAMS\\Bio Speak\\Bio Speak Studio.lnk" "$INSTDIR\\desktop\\BioSpeakStudio.exe"
    CreateShortCut "$SMPROGRAMS\\Bio Speak\\Bio Speak Browser.lnk" "$INSTDIR\\browser\\index.html"
    CreateShortCut "$SMPROGRAMS\\Bio Speak\\Bio Speak Terminal.lnk" "$INSTDIR\\terminal\\biospeak.exe"
    CreateShortCut "$SMPROGRAMS\\Bio Speak\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"

    CreateShortCut "$DESKTOP\\Bio Speak.lnk" "$INSTDIR\\launcher\\BioSpeakWelcome.exe"

    WriteRegStr HKCU "Software\\BioSpeak" "Install_Dir" "$INSTDIR"
SectionEnd

Section "Uninstall"
    Delete "$DESKTOP\\Bio Speak.lnk"
    Delete "$SMPROGRAMS\\Bio Speak\\Bio Speak Studio.lnk"
    Delete "$SMPROGRAMS\\Bio Speak\\Bio Speak Browser.lnk"
    Delete "$SMPROGRAMS\\Bio Speak\\Bio Speak Terminal.lnk"
    Delete "$SMPROGRAMS\\Bio Speak\\Uninstall.lnk"
    RMDir /r "$SMPROGRAMS\\Bio Speak"
    RMDir /r "$INSTDIR"
    DeleteRegKey HKCU "Software\\BioSpeak"
SectionEnd

Function .onInstSuccess
    ExecShell "open" "$INSTDIR\\launcher\\BioSpeakWelcome.exe"
FunctionEnd
