# 🔐 Code Signing Guide for Effortrak

This guide explains how to digitally sign your `.exe` or `.msi` files on Windows using `signtool.exe`.

---

## ✅ Step 1: Install Windows SDK

To get `signtool.exe`, install the **Windows SDK**:

🔗 https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/

Typical path to `signtool.exe` (adjust version if needed):

```
C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe
```

---

## ✅ Step 2: Generate a Self-Signed Certificate (for testing)

> ⚠️ This will not remove "Unknown Publisher" warnings. Only for internal testing.

Run this in **PowerShell**:

```powershell
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Effortrak Dev Cert" -CertStoreLocation "Cert:\CurrentUser\My"
Export-PfxCertificate -Cert $cert -FilePath ".\mycert.pfx" -Password (ConvertTo-SecureString -String "mypassword" -Force -AsPlainText)
```

---

## ✅ Step 3: Sign Your Executable

```powershell
& "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe" sign `
    /f "mycert.pfx" `
    /p "mypassword" `
    /fd sha256 `
    /tr http://timestamp.sectigo.com `
    /td sha256 `
    "Effortrak.exe"
```

📌 Replace paths and filenames as needed.

---

## ✅ Step 4: Verify the Signature

```powershell
& "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe" verify /pa /v "Effortrak.exe"
```

You should see:
```
Successfully verified: Effortrak.exe
```

---

## ⚠️ Why You Still See "Unknown Publisher"

Even after signing, Windows will still show **"Unknown Publisher"** unless:

- You use a **real certificate** issued by a trusted Certificate Authority (CA)

Trusted certs include:
- [Sectigo](https://sectigo.com)
- [DigiCert](https://www.digicert.com)
- [SSL.com](https://www.ssl.com)

---

## ✅ Timestamp Servers (Choose Any)

- http://timestamp.sectigo.com
- http://timestamp.digicert.com
- http://tsa.starfieldtech.com

---

## 💡 Bonus: Tips

- Use `--manifest` with PyInstaller to request elevation (UAC prompt)
- Sign both your `.exe` and the final `EffortrakSetup.exe` installer

---

If you're distributing publicly or commercially, consider buying a proper code signing certificate from a trusted CA.
