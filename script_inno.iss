; ============================
; Instalador IT032 - DIKOIN
; ============================

[Setup]
AppName=IT 03.2 - Convección Natural y Forzada
AppVersion=1.0.0
AppPublisher=DIKOIN
DefaultDirName={autopf}\DIKOIN\IT032_TorreConveccion
DefaultGroupName=DIKOIN
OutputBaseFilename=IT032_TorreConveccion_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "C:\Users\dikoi\IT032\dist\IT032\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\IT 03.2 - Convección"; Filename: "{app}\IT032.exe"
Name: "{commondesktop}\IT 03.2 - Convección"; Filename: "{app}\IT032.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el Escritorio"; GroupDescription: "Opciones adicionales:"; Flags: unchecked

[Run]
Filename: "{app}\IT032.exe"; Description: "Iniciar IT 03.2 - Convección"; Flags: nowait postinstall skipifsilent
