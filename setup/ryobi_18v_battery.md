# Configuring the rover for a Ryobi ONE+ 18V battery

**Important**: Do these steps **after** [rpi setup](rpi.md) and **before** the first [rover bringup](rover_bringup.md). The stock settings are for a 4S LiPo. If you power up and drive the rover on a higher-voltage battery with them, the Roboclaws stop the motors with a voltage error, and the drive motors get more than their rated 12V.

The default build runs on a 4S LiPo, which goes from 16.8V when full down to about 14V when empty. If you power the rover from a higher-voltage battery, you have to change some Roboclaw and software settings. The main example is a **Ryobi ONE+ 18V** tool pack: 5 cells (5S) Li-ion, about 20.5–21V full, 18V nominal and about 15V empty.

This page covers the settings on the Roboclaws and in this repository. Wiring, the parts list, the hardware compatibility table and the low-voltage cutoff are in [Customized Parts: Ryobi ONE+ 18V battery power supply](https://github.com/Team-Turtlebots/open-source-rover/blob/master/parts_list/customized_parts.md#1-ryobi-one-18v-battery-power-supply) in the open-source-rover repo. Finish the hardware there first.

> [!WARNING]
> Don't go above 5S (about 21V). Diode D1 on the PCB (STPS10L25D) is rated for 25V, which leaves only about 4V of headroom.

> [!WARNING]
> Nothing on the rover protects the battery from over-discharge. The rover software only *reports* the battery voltage and never stops anything because of it. The Roboclaws' Min Main Battery setting only stops the drive motors, while the Raspberry Pi and servos keep draining the pack. You **must** add the external low-voltage cutoff (set to about 15V) described in the open-source-rover guide.

## 1. Configure the Roboclaws

In Basicmicro Motion Studio, change these settings on **each** of the three Roboclaws (addresses 128, 129 and 130):

| Setting | Stock 4S value | 5S (ONE+) value | Why |
| --- | --- | --- | --- |
| Max Main Battery | 18.5V | **22V** | A full pack is about 21V. The stock value triggers "Main voltage High Error" and stops the motors. |
| Min Main Battery | 11.5V | **15V** | Stops the drive motors before the pack is over-discharged. |
| Max current (per channel) | default | **~5A** (≤7A) | Limits heating and stall current, which is higher at 21V. |

Click **Device > Write Settings** on each Roboclaw so the settings are saved.

If you skip the Max Main Battery change, the drive motors don't move, and the rover driver logs an error like this in the bringup terminal (error bit `0x8`):

```
[roboclaw_wrapper-1] [ERROR] [timestamp] [roboclaw_wrapper]: Motor controller 128 reported error code 8 (hex: 0x8),
[roboclaw_wrapper-1] Main voltage High Error
```

## 2. Lower the duty factor in the rover software

By default the rover code sends open-loop **duty** commands to the Roboclaws (`duty_mode: true` in [roboclaw_params.yaml](../ROS/osr_bringup/config/roboclaw_params.yaml)). A duty command sets a fraction of the battery voltage, so the average voltage a motor sees is *duty × battery voltage*. With the default `velocity_qpps_to_duty_factor: 8`, the fastest command maps to about 68% duty.

| Battery | `velocity_qpps_to_duty_factor` | Max duty | Max average motor voltage |
| --- | --- | --- | --- |
| 4S LiPo, full (16.8V) | 8 | 68% | ~11.5V |
| 5S ONE+, full (21V) | 8 | 68% | **~14.3V** (overvolts the 12V motors) |
| 5S ONE+, full (21V) | **7** | 60% | ~12.6V |
| 5S ONE+, nominal (18V) | **7** | 60% | ~10.8V |

On the Raspberry Pi, open the Roboclaw parameter file:

```commandline
cd ~/osr_ws/src/osr-rover-code/ROS/osr_bringup/config
nano roboclaw_params.yaml
```

Change the `velocity_qpps_to_duty_factor` line to:

```yaml
    velocity_qpps_to_duty_factor: 7  # was 8; lowered for a 5S (18V) battery
```

The factor must be an integer. This keeps the motors near their 12V rating and keeps commanded speeds close to actual speeds.

> [!NOTE]
> Make this change in `roboclaw_params.yaml` itself. [osr_launch.py](../ROS/osr_bringup/launch/osr_launch.py) loads only that file. It doesn't read `roboclaw_params_mod.yaml`.

If you built the workspace with `colcon build --symlink-install` as in [rpi setup](rpi.md), the change takes effect the next time you launch the rover. Otherwise, rebuild first:

```commandline
cd ~/osr_ws
python3 -m colcon build --symlink-install
```

**Alternative:** set `duty_mode: false` in the same file to use the Roboclaws' closed-loop velocity control instead. It only applies the duty each speed needs, whatever the battery voltage. It depends on well-tuned velocity PID values on every Roboclaw, though.

## 3. First power-up checklist

1. With the rover's main switch **off**, connect the battery lead to J1.
2. Switch on. Measure between test points T4 (`swt_out`) and T2 (`Batt-`). Expect about 18–21V, depending on charge.
3. Check the 5V and 12V test points (see [Test all voltage lines](https://github.com/Team-Turtlebots/open-source-rover/blob/master/electrical/pcb/README.md#310-test-all-voltage-lines)).
4. Run the test scripts from the `scripts` folder and confirm that the battery voltage readings match your multimeter:

   ```commandline
   cd ~/osr_ws/src/osr-rover-code/scripts
   python3 roboclawtest.py 128
   python3 roboclawtest.py 129
   python3 roboclawtest.py 130
   python3 test_ina260.py
   ```

   `roboclawtest.py` prints the Roboclaw input voltage in tenths of a volt, so `198` means 19.8V.
5. Confirm that Motion Studio shows no voltage errors on any Roboclaw.
6. Continue with [rover bringup](rover_bringup.md). When you first launch the rover, watch the terminal for Roboclaw voltage errors.
7. Drive gently at first. Check the motor temperatures after a few minutes.

## Operating notes

- **Runtime:** expect roughly 2 hours of mixed driving and idling per 4Ah ONE+ pack.
- **Use one pack at a time.** Never connect packs in parallel or in series.
- **Remove the pack** when the rover is stored, so the low-voltage cutoff module and the electronics don't slowly drain it.
- **Charge off the rover**, with the Ryobi charger.
- The `battery_state` topic from the INA260 node always reports `POWER_SUPPLY_TECHNOLOGY_LIPO`, whatever battery you use. The voltage and current values are still correct.
- The main open-source-rover README says the rover "powers down below 13–14V". That doesn't apply here: nothing on the board enforces it, and a ONE+ pack reaches its cutoff before that range.

## Going back to a 4S LiPo

Undo both changes: set Max Main Battery back to 18.5V and Min Main Battery to 11.5V on all three Roboclaws, and set `velocity_qpps_to_duty_factor` back to `8`.
