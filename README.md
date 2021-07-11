# forward-hwinfo-influxdb
Personal project to forward sensor data from hwinfo to influxdb

Use NSSM to setup a Windows service.

```
# Install/Start
cd C:\forward-hwinfo-influxdb
nssm.exe install "Forward Hwinfo To Influxdb" "C:\forward-hwinfo-influxdb\venv\Scripts\python.exe" "C:\forward-hwinfo-influxdb\forward-hwinfo-influxdb.py"
nssm.exe start "Forward Hwinfo To Influxdb"

# Stop/Remove
nssm.exe stop "Forward Hwinfo To Influxdb"
nssm.exe remove "Forward Hwinfo To Influxdb"

# Enable logging if necessary
nssm set "Forward Hwinfo To Influxdb" AppStdout C:\forward-hwinfo-influxdb\logs\service.log
nssm set "Forward Hwinfo To Influxdb" AppStderr C:\forward-hwinfo-influxdb\logs\service-error.log
```