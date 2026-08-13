# Bundled offline detector

This directory is the dashboard's zero-configuration fallback model location.
`robot_server.vision.VisionManager` uses `yolov4-tiny.cfg` and
`yolov4-tiny.weights` from here whenever the corresponding environment paths
are unset. Both files are loaded locally through OpenCV DNN; the Pi does not
need internet access at runtime.
