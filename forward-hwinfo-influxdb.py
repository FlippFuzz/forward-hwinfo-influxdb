import platform
import time
from winreg import ConnectRegistry, OpenKey, EnumValue, QueryInfoKey, KEY_READ, HKEY_USERS
from influxdb_client import InfluxDBClient, Point, WritePrecision, WriteOptions
from credentials import credentials


# Example of how to create windows service:
# http://thepythoncorner.com/dev/how-to-create-a-windows-service-in-python/
# https://www.oreilly.com/library/view/hands-on-software-engineering/9781788622011/66a35121-d465-4318-b566-264dc91b5829.xhtml


class SensorData:
    def __init__(self):
        self.sensor = None
        self.label = None
        self.valueRaw = None

    def __str__(self):
        return f"({self.sensor}, {self.label}, {self.valueRaw})"


# HWiNFO's sensor data can be forwarded to Window registry
# First step is to read the sensor data from Window registry and store them in a list
while True:
    all_sensor_data: list[SensorData] = []

    with ConnectRegistry(None, HKEY_USERS) as reg:
        with OpenKey(reg, f"{credentials.windows_sid}\\SOFTWARE\\HWiNFO64\\VSB", 0, KEY_READ) as reg_key:
            num_of_values = QueryInfoKey(reg_key)[1]
            for i in range(num_of_values):
                values = EnumValue(reg_key, i)
                if values[0].startswith("Sensor"):
                    new_data = SensorData()
                    new_data.sensor = values[1]
                    all_sensor_data.append(new_data)
                elif values[0].startswith("Label"):
                    all_sensor_data[-1].label = values[1]
                elif values[0].startswith("ValueRaw"):
                    try:
                        value_raw = float(values[1])
                    except ValueError:
                        value_raw = values[1]
                    if values[1] == "Yes":
                        value_raw = True
                    elif values[1] == "No":
                        value_raw = False
                    all_sensor_data[-1].valueRaw = value_raw
                # Not going to care about colour or value. Just forget about them

    # Now, go through the list of sensor data and create the InfluxDB points
    cpu = Point("cpu").tag("host", platform.node())
    motherboard = Point("motherboard").tag("host", platform.node())
    gpu = Point("gpu").tag("host", platform.node())
    psu = Point("psu").tag("host", platform.node())
    smart = []

    for data in all_sensor_data:
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
            disk_tag = data.sensor.split(":")[1].split("(")[0].strip()
            smart.append(Point("smart").tag("host", platform.node()).tag("disk", disk_tag)
                         .field(data.label, data.valueRaw))
        else:
            print(f"Unused {data}")

    # Finally, write points to Influx
    influx_client = InfluxDBClient(url=credentials.influx_url, token=credentials.influx_token,
                                   org=credentials.influx_org, timeout=1 * 60 * 60 * 1000)

    write_api = influx_client.write_api(write_options=WriteOptions(batch_size=50_000, flush_interval=10_000))
    write_api.write(bucket=credentials.influx_bucket, record=cpu, WritePrecision=WritePrecision.S)
    write_api.write(bucket=credentials.influx_bucket, record=motherboard, WritePrecision=WritePrecision.S)
    write_api.write(bucket=credentials.influx_bucket, record=gpu, WritePrecision=WritePrecision.S)
    write_api.write(bucket=credentials.influx_bucket, record=psu, WritePrecision=WritePrecision.S)
    write_api.write(bucket=credentials.influx_bucket, record=smart, WritePrecision=WritePrecision.S)

    write_api.flush()
    write_api.close()

    # Get data once every 60s
    time.sleep(60)
