# J.A.R.V.I.S. Android & Scrcpy DeX Studio v3.0.0 (Flagship Obsidian Glass Edition)

## Overview

J.A.R.V.I.S. Android & Scrcpy DeX Studio is a cutting-edge development environment for Android enthusiasts and developers. It combines the power of Android with the flexibility of a desktop workstation, providing a seamless experience for both development and productivity.

## Architecture Overview

| Component                | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| **2-Pane Obsidian Glass Navigation Rail** | A sleek, modern navigation interface for easy access to features. |
| **Magnetic Android Emulator Side-Toolbar** | A dockable toolbar for the Android Emulator, enhancing usability. |
| **Scrcpy Mirror via Win32/xdotool** | Mirrors Android screen on PC, supporting Windows and Linux. |
| **PC as Samsung DeX / Android Desktop Workstation** | Utilizes Scrcpy 4.0 to turn your PC into an Android desktop. |
| **Multi-APK Batch Installer** | A modal for batch installing APKs with a 60fps progress bar. |
| **Live System Task Manager** | A real-time task manager with supersampled radial gauges and glowing sparklines. |
| **App Manager & Hardware Telemetry** | Manages installed apps and provides detailed hardware telemetry. |

## Key Features

- **2-Pane Obsidian Glass Navigation Rail**: A modern, intuitive navigation interface for quick access to all features.
- **Magnetic Android Emulator Side-Toolbar**: A dockable toolbar for the Android Emulator, enhancing usability.
- **Scrcpy Mirror via Win32/xdotool**: Mirrors Android screen on PC, supporting Windows and Linux.
- **PC as Samsung DeX / Android Desktop Workstation**: Utilizes Scrcpy 4.0 to turn your PC into an Android desktop.
- **Multi-APK Batch Installer**: A modal for batch installing APKs with a 60fps progress bar.
- **Live System Task Manager**: A real-time task manager with supersampled radial gauges and glowing sparklines.
- **App Manager & Hardware Telemetry**: Manages installed apps and provides detailed hardware telemetry.

## Installation

### Windows 11

#### Setup EXE
```bash
# Download the setup executable
wget https://github.com/Forgejo/J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio/releases/download/v3.0.0/J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio-v3.0.0-Setup.exe

# Run the setup executable
J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio-v3.0.0-Setup.exe
```

#### Portable --onefile EXE
```bash
# Download the portable executable
wget https://github.com/Forgejo/J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio/releases/download/v3.0.0/J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio-v3.0.0-Portable.exe

# Run the portable executable
J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio-v3.0.0-Portable.exe
```

### Arch/CachyOS Linux

#### PKGBUILD / makepkg -si
```bash
# Clone the repository
git clone https://github.com/Forgejo/J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio.git

# Navigate to the cloned directory
cd J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio

# Build and install the package
makepkg -si
```

### Debian/Ubuntu

#### .deb
```bash
# Download the .deb package
wget https://github.com/Forgejo/J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio/releases/download/v3.0.0/J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio-v3.0.0.deb

# Install the .deb package
sudo dpkg -i J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio-v3.0.0.deb
```

## Build Instructions

### Prerequisites

- **Python 3.8+**: Ensure Python 3.8 or higher is installed.
- **Scrcpy 4.0**: Install Scrcpy 4.0 for Android screen mirroring.
- **Build Tools**: Install necessary build tools for your operating system.

### Steps

1. **Clone the Repository**
    ```bash
    git clone https://github.com/Forgejo/J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio.git
    cd J.A.R.V.I.S.-Android-Scrcpy-DeX-Studio
    ```

2. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Build the Application**
    ```bash
    python setup.py build
    ```

4. **Install the Application**
    ```bash
    python setup.py install
    ```

## Contributing

We welcome contributions from the community! Please follow our [Contribution Guidelines](CONTRIBUTING.md) to get started.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any inquiries or support, please contact us at [support@forgejo.com](mailto:support@forgejo.com).

---

This README provides a comprehensive overview of J.A.R.V.I.S. Android & Scrcpy DeX Studio, detailing its features, installation instructions, and build process.
