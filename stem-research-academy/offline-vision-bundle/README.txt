3TSAHUR OFFLINE DETECTOR INSTALL

1. Copy this entire folder to a USB drive.
2. Plug the USB drive into the Raspberry Pi.
3. Open this folder on the Pi and open a terminal here.
4. Run exactly:

   bash install.sh

Do not use sudo before bash. The script verifies the model, installs it,
enables detection at service startup, restarts the dashboard, and performs a
local health check. The Raspberry Pi does not need Wi-Fi or internet.
