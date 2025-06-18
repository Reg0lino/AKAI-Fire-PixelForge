#define MyAppName "Akai Fire PixelForge"
#define MyAppVersion "1.5.0"
#define MyAppPublisher "Reg0lino"
#define MyAppURL "https://github.com/Reg0lino/Akai_Fire_PixelForge"
#define MyAppExeName "Akai Fire PixelForge.exe" 
#define MyBuildOutputDir "dist\" + MyAppName 
#define MyStarterPackSourceDir "Installer_Content\StarterPack" 
#define MyUserPresetsBaseFolderName "Akai Fire RGB Controller User Presets" 

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=Setup_{#MyAppName}_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Components]
Name: "main"; Description: "Main Program Files"; Types: full compact custom; Flags: fixed
Name: "starterpack"; Description: "Install Example Presets (Recommended)"; Types: full custom

[Files]
Source: "{#MyBuildOutputDir}\*"; DestDir: "{app}"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation files
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.txt"; DestDir: "{app}"; Flags: ignoreversion ;
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; Starter Pack - ensure paths are correct relative to the .iss file location
Source: "{#MyStarterPackSourceDir}\sequences\user\*"; DestDir: "{userdocs}\{#MyUserPresetsBaseFolderName}\sequences\user"; Components: starterpack; Flags: recursesubdirs createallsubdirs uninsneveruninstall
Source: "{#MyStarterPackSourceDir}\OLEDCustomPresets\TextItems\*"; DestDir: "{userdocs}\{#MyUserPresetsBaseFolderName}\OLEDCustomPresets\TextItems"; Components: starterpack; Flags: recursesubdirs createallsubdirs uninsneveruninstall
Source: "{#MyStarterPackSourceDir}\OLEDCustomPresets\ImageAnimations\*"; DestDir: "{userdocs}\{#MyUserPresetsBaseFolderName}\OLEDCustomPresets\ImageAnimations"; Components: starterpack; Flags: recursesubdirs createallsubdirs uninsneveruninstall
Source: "{#MyStarterPackSourceDir}\static\user\*"; DestDir: "{userdocs}\{#MyUserPresetsBaseFolderName}\static\user"; Components: starterpack; Flags: recursesubdirs createallsubdirs uninsneveruninstall


[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"; Check: WizardIsTaskSelected('desktopicon')

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent unchecked
Filename: "{app}\README.txt"; Description: "View Readme File (Important Info Inside)"; Flags: postinstall shellexec skipifsilent unchecked

[Messages]
SetupAppTitle=Setup - {#MyAppName}
SetupWindowTitle={#MyAppName} Setup
WelcomeLabel1=Welcome to the {#MyAppName} Setup Wizard.
WelcomeLabel2=This wizard will install {#MyAppName} version {#MyAppVersion} on your computer.\n\n<B>Important Note on Antivirus Software:</B>\nAs an independently developed application that is not yet digitally signed, some antivirus programs may show a warning during installation or when the application saves your custom presets (to your 'My Documents' folder).\n\nThis is often a precaution for new software. Official downloads of {#MyAppName} from the GitHub releases page are safe. If prompted by your antivirus, please choose to "Allow" the action. For more details, please see the Readme file after installation.\n\nThank you for your understanding!
BeveledLabel=Please review the information above before continuing.