import platform
from winreg import ConnectRegistry, OpenKey, KEY_ALL_ACCESS, EnumValue, QueryInfoKey, HKEY_CURRENT_USER
from influxdb_client import InfluxDBClient, Point, WritePrecision, WriteOptions
from credentials import credentials


class SensorData:
    def __init__(self):
        self.sensor = None
        self.label = None
        self.valueRaw = None

    def __str__(self):
        return f"({self.sensor}, {self.label}, {self.valueRaw})"


# HWiNFO's sensor data can be forwarded to Window registry
# First step is to read the sensor data from Window registry and store them in a list
allSensorData = []

with ConnectRegistry(None, HKEY_CURRENT_USER) as reg:
    with OpenKey(reg, r"SOFTWARE\HWiNFO64\VSB", 0, KEY_ALL_ACCESS) as reg_key:
        num_of_values = QueryInfoKey(reg_key)[1]
        for i in range(num_of_values):
            values = EnumValue(reg_key, i)
            if values[0].startswith("Sensor"):
                newData = SensorData()
                newData.sensor = values[1]
                allSensorData.append(newData)
            elif values[0].startswith("Label"):
                allSensorData[-1].label = values[1]
            elif values[0].startswith("ValueRaw"):
                valueRaw = values[1]
                if values[1] == "Yes":
                    valueRaw = True
                elif values[1] == "No":
                    valueRaw = False
                allSensorData[-1].valueRaw = valueRaw
            # Not going to care about colour or value. Just forget about them

# Now, go through the list of sensor data and create the InfluxDB points
cpu = Point("cpu").tag("host", platform.node())
motherboard = Point("motherboard").tag("host", platform.node())
gpu = Point("gpu").tag("host", platform.node())
psu = Point("psu").tag("host", platform.node())
smart = []

for data in allSensorData:
    if data.sensor is None:
        continue
    elif data.sensor.startswith("CPU"):
        cpu.field(data.label, data.valueRaw)
    elif data.sensor.startswith("ASRock"):
        motherboard.field(data.label, data.valueRaw)
    elif data.sensor.startswith("GPU"):
        gpu.field(data.label, data.valueRaw)
    elif data.sensor.startswith("Corsair"):
        psu.field(data.label, data.valueRaw)
    elif data.sensor.startswith("S.M.A.R.T."):
        if data.label == "Drive Airflow Temperature":  # Do a rename so that they look the same
            data.label = "Drive Temperature"
        diskTag = data.sensor.split(":")[1].split("(")[0].strip()
        smart.append(Point("smart").tag("host", platform.node()).tag("disk", diskTag).field(data.label, data.valueRaw))
    else:
        print(f"Unused {data}")

# Finally, write points to Influx
influxClient = InfluxDBClient(url=credentials.influx_url, token=credentials.influx_token,
                              org=credentials.influx_org, timeout=1 * 60 * 60 * 1000)

write_api = influxClient.write_api(write_options=WriteOptions(batch_size=50_000, flush_interval=10_000))
write_api.write(bucket=credentials.influx_bucket, record=cpu, WritePrecision=WritePrecision.S)
write_api.write(bucket=credentials.influx_bucket, record=motherboard, WritePrecision=WritePrecision.S)
write_api.write(bucket=credentials.influx_bucket, record=gpu, WritePrecision=WritePrecision.S)
write_api.write(bucket=credentials.influx_bucket, record=psu, WritePrecision=WritePrecision.S)
write_api.write(bucket=credentials.influx_bucket, record=smart, WritePrecision=WritePrecision.S)

write_api.flush()
write_api.close()
