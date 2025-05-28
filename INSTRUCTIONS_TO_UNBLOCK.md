# How to Unblock Akai_Fire_PixelForge.exe on Windows

If you see a "Windows protected your PC" (SmartScreen) popup when trying to run the application, or if the application doesn't start correctly, you might need to "unblock" the downloaded executable file. This is a common security measure by Windows for files downloaded from the internet.

**Here's how to do it:**

1.  **Locate the Executable:**
    After unzipping the archive, find the `AkaiFireControllerApp.exe` file (or `AkaiFireControllerApp_Debug.exe` if you're using the debug version) in the extracted folder.

2.  **Open File Properties:**
    Right-click on the `.exe` file and select **"Properties"** from the context menu.

3.  **Check for an "Unblock" Option:**
    In the "Properties" window, look at the **"General"** tab. Towards the bottom, you might see a security warning like:
    *"This file came from another computer and might be blocked to help protect this computer."*
    Next to this message, there should be an **"Unblock" checkbox** or an "Unblock" button.

4.  **Unblock the File:**
    *   If you see the **"Unblock" checkbox**, check it.
    *   If you see an **"Unblock" button**, click it.

5.  **Apply Changes:**
    Click **"Apply"** and then **"OK"**.

6.  **Try Running Again:**
    Now, try running the `AkaiFireControllerApp.exe` again. It should start without the SmartScreen warning (or related issues if it was a silent block).

**What if I don't see the "Unblock" option?**

*   If you unzipped the archive and there's no "Unblock" option on the `.exe` file itself, try unblocking the **original .zip file *before* you extract it.** Then, extract the files again. Sometimes, Windows applies the "blocked" status to all files extracted from a blocked archive.
*   Ensure you have administrator privileges if prompted.

If you continue to have issues, contact the developer via Github.