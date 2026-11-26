# TurtleBots Guide: Rover Software

This guide sets up everything you need to work on the rover's software, step by step. It has
three parts:

| Part | What you get | Who needs it |
| --- | --- | --- |
| [**1. Set up your PC**](#part-1-set-up-your-pc) | Linux (Ubuntu) on your Windows computer, and a copy of the rover code | Everyone |
| [**2. Work on the real rover**](#part-2-work-on-the-real-rover) | Log in to the rover's Raspberry Pi, put new code on it, and run it | Anyone working with the real rover |
| [**3. Set up the simulation**](#part-3-set-up-the-simulation) | A 3D model of the rover that drives around on your screen. You don't need the real rover. | Anyone who wants to test code without the rover |

You don't need to know anything about Linux, WSL, Docker, or ROS before you start. Parts 1 and 3
take about **1–2 hours** the first time. Most of that is waiting for downloads.

> [!TIP]
> Each box with a gray background is a **command**. Copy it, paste it into the window the step
> names, and press **Enter**. Wait until the command finishes before running the next one.

---

## What are all these things?

| Name | What it is, in one sentence |
| --- | --- |
| **WSL** (Windows Subsystem for Linux) | Lets you run Linux, a different operating system, inside Windows. |
| **Ubuntu** | The version of Linux we install inside WSL. The rover's Pi runs Ubuntu too. |
| **Terminal** | A window where you type commands instead of clicking buttons. |
| **git** and **GitHub** | git keeps track of changes to the code. GitHub is the website that stores the team's copy. |
| **Docker** | A tool that runs a "container": a sealed box with all the software the simulation needs already installed. |
| **Image** | The recipe-plus-ingredients for a container. We build it once and reuse it. |
| **rocker** | A helper that starts a Docker container and lets it open windows on your screen. |
| **ROS 2** | The robot software the real rover runs. The simulation uses the same code. |
| **Gazebo** | The 3D simulator that shows the rover and its physics. |
| **Raspberry Pi** (or "Pi") | The small computer inside the rover that runs its software. Ours is a Pi 5. |
| **SSH** | A way to type commands on the Pi from your own computer, over Wi-Fi. |

Here's how they fit together:

```text
                          ┌─▶  SSH over Wi-Fi  ─▶  rover's Raspberry Pi  ─▶  ROS 2  ─▶  real rover   (Part 2)
Windows  ─▶  WSL + Ubuntu ┤
                          └─▶  Docker container  ─▶  ROS 2 + Gazebo  ─▶  rover on your screen   (Part 3)
```

The team's code is stored on **GitHub**. For now, we save changes to GitHub **from the Pi**
(`git push`), and every computer gets the newest code with `git pull`. Pushing from your own PC
needs a GitHub login, which we'll set up later.

---

## Before you start

You need:

- A Windows 10 (version 22H2) or Windows 11 computer.
- An administrator password for that computer (ask a parent or teacher if you don't have one).
- About **15 GB of free disk space** (most of it for the simulation).
- A good internet connection.

---

## Part 1: Set up your PC

Everyone does this part. At the end, you have Ubuntu running on your Windows computer and your
own copy of the rover code.

### 1.1 Install WSL and Ubuntu

1. Click the **Start** button, type `PowerShell`, right-click **Windows PowerShell**, and choose
   **Run as administrator**. Click **Yes** if Windows asks for permission.
2. In the blue PowerShell window, run:

   ```powershell
   wsl --install -d Ubuntu
   ```

3. When it says it's finished, **restart your computer**.
4. After the restart, an **Ubuntu** window opens on its own. If it doesn't, click **Start**, type
   `Ubuntu`, and open it.
5. Ubuntu asks you to make a **username** and **password**:
   - Use a short username with only lowercase letters, for example `alex`.
   - When you type the password, **nothing shows up on screen**. That's normal, so just keep
     typing and press **Enter**.
   - **Write the password down.** You'll need it every time a command starts with `sudo`.

6. Update Ubuntu's software list and install the latest updates:

   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

**Check:** in PowerShell (it doesn't need to be an administrator window this time), run `wsl --version`.
You should see a list of version numbers, including a line starting with `WSLg version`. WSLg is
the part that lets Linux programs open windows on your Windows screen.

> [!NOTE]
> From now on, **"the Ubuntu terminal"** means the Ubuntu window from step 4. Every command in
> this guide goes there unless the step says **PowerShell**.

---

### 1.2 Get the rover code

1. Install `git`, the tool that downloads code from GitHub:

   ```bash
   sudo apt install -y git
   ```

2. Download the rover code into your home folder:

   ```bash
   cd ~
   git clone https://github.com/Team-Turtlebots/osr-rover-code.git
   ```

3. Go into the folder you just downloaded:

   ```bash
   cd ~/osr-rover-code
   ```

**Check:** run `ls`. You should see `Dockerfile`, `README.md`, and a folder named `ROS`.

---

## Part 2: Work on the real rover

The rover's software runs on its **Raspberry Pi 5**, which has **Ubuntu 24.04** and **ROS 2
Jazzy**. You don't plug a screen into it. Instead, you log in from your PC over Wi-Fi with SSH
and type commands there. Do [Part 1](#part-1-set-up-your-pc) first. You don't need Part 3.

### 2.1 Log in to the Pi

1. Turn on the rover and wait about a minute for the Pi to start.
2. Make sure your PC is on the **same Wi-Fi network** as the rover.
3. In the Ubuntu terminal, run:

   ```bash
   ssh pi@192.168.68.80
   ```

   The first time, it asks `Are you sure you want to continue connecting?`. Type `yes` and press
   **Enter**. Then type the password. As in Ubuntu, nothing shows up while you type it.

The rover's Pi uses this login:

- **User:** `pi`
- **Password:** `Ttbots2026`
- **IP address:** `192.168.68.80`

**Check:** the prompt changes to `(venv) pi@TurtleBots:~$`. Every command you type now runs **on
the Pi**, not on your PC. `(venv)` means the rover's Python environment is already switched on.
To log out and go back to your PC, type `exit`.

If `ssh` says `Connection timed out` or `No route to host`, the Pi isn't on your network yet, or
its IP address changed:

- `192.168.68.80` is the Pi's address on our **home Wi-Fi**. On a **phone hotspot** it gets a
  different one. To find it, open the hotspot settings on the phone and look at the list of
  connected devices for `TurtleBots`.
- Or use the Pi's name instead of its address. Run this in **PowerShell**, not in the Ubuntu
  terminal, because Ubuntu in WSL usually can't look up `.local` names:

  ```powershell
  ssh pi@TurtleBots.local
  ```

> [!TIP]
> Open a second Ubuntu window and log in again when you need two terminals on the Pi at once,
> for example one to run the rover and one to check it.

---

### 2.2 What's where on the Pi

| Folder | What's in it |
| --- | --- |
| `~/osr_ws` | The ROS **workspace**: where the rover code is built |
| `~/osr_ws/src/osr-rover-code` | The rover code, a git copy of the team's GitHub repo |
| `~/osr_ws/venv` | The rover's Python environment (extra Python packages) |
| `~/osr_ws/install` | The built code. ROS runs it from here. |
| `~/osr_ws/src/camera_ros`, `~/libcamera` | Camera software built for the [camera guide](TTB-Camera.md) |
| `~/bio_data` | Photos and the observation log from the [phone page](ROS/osr_biodiversity/README.md) |

---

### 2.3 Get the newest code onto the Pi

For now, the Pi is where we save changes to GitHub: it's already logged in to GitHub, and our
PCs aren't yet. So whenever you change code on the Pi, commit and push it (steps 1 and 2), so the
change is saved on GitHub and nobody's work gets lost.

1. Go to the rover code and check for changes made on the Pi itself:

   ```bash
   cd ~/osr_ws/src/osr-rover-code
   git status
   ```

   If it says **`nothing to commit, working tree clean`**, go on to step 2.

   If it lists changed files, someone edited code on the Pi, for example to tune the controller
   buttons. Commit those changes first, so `git pull` doesn't clash with them:

   ```bash
   git add -A
   git commit -m "Say what you changed, e.g. Tune controller buttons"
   ```

   Not sure whether a change should be kept? Ask a teammate before you commit it.

2. Download the newest code from GitHub:

   ```bash
   git pull --rebase
   ```

   `--rebase` puts any changes you committed in step 1 on top of the newest code from GitHub.
   Without it, git stops with `Need to specify how to reconcile divergent branches` when both
   the Pi and GitHub have new changes.

   If you committed something in step 1, also run `git push` to send it to GitHub.

3. Install any new software the code needs:

   ```bash
   cd ~/osr_ws
   rosdep install --from-paths src --ignore-src --rosdistro=jazzy -y --skip-keys=libcamera
   ```

   `--skip-keys=libcamera` keeps rosdep from installing a second libcamera that can't use the
   Pi 5's camera (see the [camera guide](TTB-Camera.md)).

4. Build the code, then tell this terminal about the new build:

   ```bash
   python3 -m colcon build --symlink-install
   source install/setup.bash
   ```

**Check:** the build ends with `Summary: ... packages finished` and no `failed`.

> [!TIP]
> To build just one package, which is much faster, add `--packages-select` and the package's
> name, for example `python3 -m colcon build --symlink-install --packages-select osr_biodiversity`.

---

### 2.4 Run the rover

The Pi starts the rover's driving software by itself when it turns on, using the **startup
service** (`osr_startup.service`). On our rover the service is turned on, so you don't need to
start the driving software yourself. After new code, restart it so the rover uses that code:

```bash
sudo systemctl restart osr_startup.service
```

To run the rover **by hand** instead (to see its messages, for example), stop the service
first. Otherwise two copies of the software fight over the motors:

```bash
sudo systemctl stop osr_startup.service
ros2 launch osr_bringup osr_mod_launch.py
```

Press **Ctrl + C** to stop it.

| To… | Run |
| --- | --- |
| See whether the service is running, and its last messages | `sudo systemctl status osr_startup.service` |
| Start or stop the service | `sudo systemctl start osr_startup.service` / `sudo systemctl stop osr_startup.service` |
| Make it start (or not start) when the Pi turns on | `sudo systemctl enable osr_startup.service` / `sudo systemctl disable osr_startup.service` |

More details are in the [rover bringup guide](setup/rover_bringup.md).

---

### 2.5 Camera and phone page

- [Camera guide](TTB-Camera.md): set up the Arducam OV5647 camera on the Pi 5.
- [Phone page (osr_biodiversity)](ROS/osr_biodiversity/README.md): live camera view, plant
  identification, and the observation log for Marpy.

The startup service doesn't start the camera or the phone page yet. Start them by hand in a
second terminal on the Pi:

```bash
ros2 launch osr_biodiversity biodiversity.launch.py
```

This is safe to run while the driving software is running: the phone page never moves the
rover. (To have the service start it too, see "Start it with the rover" in the
[phone page README](ROS/osr_biodiversity/README.md#start-it-with-the-rover-optional).)

---

### 2.6 Things to know about our rover

> [!IMPORTANT]
> On the **real rover**, do the [Ryobi 18V battery configuration](setup/ryobi_18v_battery.md)
> **before the first bringup** ([Rover code bringup](setup/rover_bringup.md)). The default settings
> are for a 4S LiPo. With an 18V pack, the motor controllers stop the motors with a voltage error,
> and the motors get more than their rated 12V. The simulation doesn't need this change.
>
> **Our rover runs on the Ryobi 18V battery, and this is done.** The Roboclaw voltage limits are
> set in Motion Studio, on the Roboclaws themselves. The software setting
> (`velocity_qpps_to_duty_factor: 7`) is in `ROS/osr_bringup/launch/osr_mod_launch.py`, so leave
> `roboclaw_params.yaml` at its default of `8`.

> [!NOTE]
> **Error about a missing `lgpio` / `adafruit-lgpio` package on the rover?** Don't install
> `adafruit-lgpio`. It needs Python 3.13, and the rover's Ubuntu 24.04 has Python 3.12, so pip
> refuses. Install `lgpio` instead, inside the rover's Python environment:
>
> ```bash
> cd ~/osr_ws
> source venv/bin/activate
> python3 -m pip install lgpio
> ```
>
> The [Raspberry Pi setup guide](setup/rpi.md) now installs it for you.

> [!NOTE]
> **Rover-specific settings** go in the `_mod` files: `ROS/osr_bringup/config/*_mod.yaml` and
> `ROS/osr_bringup/launch/osr_mod_launch.py`. Don't change the default files. Our repo copies
> NASA-JPL's updates every day, and changes to their files can clash with those updates.

---

## Part 3: Set up the simulation

The simulation runs the rover's real code with a 3D model of the rover, so you can try out
changes without the real rover. Do [Part 1](#part-1-set-up-your-pc) first.

### 3.1 Install Docker

We install Docker **inside Ubuntu**. You don't need Docker Desktop for Windows.

1. In the Ubuntu terminal, install Docker and two add-ons it needs:

   ```bash
   sudo apt install -y docker.io docker-buildx docker-compose-v2
   ```

2. Give your user permission to use Docker without typing `sudo` every time:

   ```bash
   sudo usermod -aG docker $USER
   ```

3. This permission only takes effect after WSL restarts. Close the Ubuntu window. Then open
   **PowerShell** and run:

   ```powershell
   wsl --shutdown
   ```

   Then open **Ubuntu** again from the Start menu.

#### Check that Docker works

Run each of these in the Ubuntu terminal:

```bash
docker --version
docker buildx version
docker run --rm hello-world
```

The last command should print **"Hello from Docker!"** If it does, Docker is ready. 🎉

| If you see… | It means… | Fix |
| --- | --- | --- |
| `permission denied ... docker.sock` | Your user isn't allowed to use Docker yet. | Redo step 2, then the `wsl --shutdown` in step 3. |
| `Cannot connect to the Docker daemon` | Docker isn't running. | Run `sudo service docker start`, then try again. |
| `docker: command not found` | Docker isn't installed. | Redo step 1. |


---

### 3.2 Build the simulation image

This step downloads ROS 2 and Gazebo and sets everything up inside a Docker image. It's the
longest step: it can take **20–60 minutes** and downloads a few gigabytes. You only have to do it
once.

In the Ubuntu terminal, make sure you're in the `osr-rover-code` folder, then run:

```bash
cd ~/osr-rover-code
docker build -t osr-rover-sim .
```

> [!IMPORTANT]
> Don't forget the **dot (`.`) at the end**. It tells Docker to use the current folder. Without
> it, you'll get an error like `requires 1 argument`.

**Check:** run `docker image ls`. You should see `osr-rover-sim` in the list.


---

### 3.3 Install rocker

`rocker` starts the container and connects it to your screen so Gazebo's window can appear.

1. Install `pipx`, a tool for installing Python programs:

   ```bash
   sudo apt install -y pipx
   pipx ensurepath
   ```

2. **Close the Ubuntu window and open a new one**, so it picks up the change from `pipx ensurepath`.
3. Install rocker:

   ```bash
   pipx install rocker
   ```

4. (Optional) Create an empty file that stops some harmless `xauth` warnings from appearing every
   time you start rocker:

   ```bash
   touch ~/.Xauthority
   ```

**Check:** `rocker --version` should print a version number, such as `0.4.0`.


---

### 3.4 Start the simulation 🚀

#### 1. Start the container

In the Ubuntu terminal, run:

```bash
rocker --x11 --name osr osr-rover-sim
```

After a few seconds, the prompt changes, for example to `root@...:~/osr_ws#`. **You're now
inside the container.** ROS 2 is already set up there.

> [!NOTE]
> - The `--x11` part lets the container open windows on your screen.
> - Ignore the `xauth: file ... does not exist` messages if you skipped step 4 of 3.3. They're
>   harmless.
> - This command draws the 3D graphics with your computer's main processor (CPU), which works
>   on every computer but can be slow. If your computer has a newer graphics chip, step 3.5 shows
>   how to use it instead.
> - Don't add `--nvidia runtime`, even if you have an NVIDIA card. It fails without extra
>   setup and doesn't make Gazebo faster. Step 3.5 explains what to do instead.

#### 2. Launch Gazebo with the rover

Inside the container, run:

```bash
ros2 launch osr_gazebo empty_world.launch.py
```

A **Gazebo** window opens with the rover in an empty world. The first launch can take a minute.
If you see a warning that Gazebo Classic has reached "end of life", ignore it. The simulation
still works.

Leave this terminal running. If you close it, the simulation stops.

#### 3. Drive the rover with your keyboard

1. Open a **second** Ubuntu window (Start → Ubuntu).
2. Connect it to the same container:

   ```bash
   docker exec -it osr bash
   ```

3. Start the keyboard controller:

   ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard
   ```

4. **Click inside this terminal window** so it receives your key presses, then use these keys:

   | Key | Action |
   | --- | --- |
   | `i` | Drive forward |
   | `,` | Drive backward |
   | `u` / `o` | Drive forward while turning left / right |
   | `m` / `.` | Drive backward while turning |
   | `j` / `l` | Point the wheels left / right (the rover doesn't move) |
   | `k` | Stop |
   | `q` / `z` | Go faster / slower |

   Watch the rover move in the Gazebo window!

> [!NOTE]
> The keyboard controller can't make the rover spin in place (rotate without driving forward). That
> needs a game controller or a special command. See the
> [osr_gazebo README](ROS/osr_gazebo/README.md) for details.

#### 4. Stop everything

- Press **Ctrl + C** in each terminal to stop the program running there.
- Type `exit` in the **first** terminal (the one where you ran `rocker`) to leave the container.

> [!WARNING]
> The container is **deleted** when you exit it. Any files you change inside the container are
> lost. That's fine for running the simulation, because the next `rocker` command starts a fresh
> one. To make a lasting change to the code, edit the files in `~/osr-rover-code` (outside the
> container), then rebuild the image (step 3.2).


---

### 3.5 (Optional) Use your graphics chip to make it faster ⚡

By default, the simulation draws its 3D graphics with the CPU. A graphics chip (GPU) is
built for exactly this job, so using one makes Gazebo much smoother. WSL can share your Windows
graphics chip with Linux, and Docker can pass it into the container.

#### Does my computer qualify?

| Your graphics | Good to try? |
| --- | --- |
| **NVIDIA** GeForce or RTX card (GTX 900 series or newer) | ✅ Yes |
| **Intel** Iris Xe or Arc (11th-gen Intel Core or newer) | ✅ Yes |
| **AMD** Radeon graphics in a Ryzen 5000-series or newer processor, or a Radeon RX card | ✅ Yes |
| Older **Intel UHD / HD Graphics** | ❌ Skip step 3.5. We tested one and the simulation froze. |

To find out what you have: press **Ctrl + Shift + Esc** to open Task Manager, click
**Performance**, and look at the entries named **GPU 0** (and **GPU 1**, if there is one). The
name of the graphics chip is in the top-right corner.

Using **Windows 11** gives the best chance of this working.

#### Step 1: Update your graphics driver in Windows

Install the newest driver **in Windows**, from the company that made your graphics chip:

- **NVIDIA:** [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx), or the NVIDIA app
- **Intel:** [Intel Driver & Support Assistant](https://www.intel.com/content/www/us/en/support/detect.html)
- **AMD:** [amd.com/support](https://www.amd.com/en/support/download/drivers.html)

Restart your computer after installing it. Then update WSL from **PowerShell**:

```powershell
wsl --update
wsl --shutdown
```

> [!WARNING]
> **Never install a graphics driver inside Ubuntu**, for example with `sudo apt install nvidia-driver-...`.
> WSL uses the Windows driver automatically, and a Linux driver installed in Ubuntu breaks it.

#### Step 2: Check that Ubuntu can see the graphics chip

Open Ubuntu and run:

```bash
ls /dev/dxg
```

It should print `/dev/dxg`. If it says `No such file or directory`, WSL can't reach your graphics
chip. Redo Step 1, and check that you're on Windows 10 22H2 or Windows 11.

With an **NVIDIA** card, also run `nvidia-smi`. It should print a table with your card's name.

#### Step 3: Start the container with the graphics chip

Use this longer command instead of the one in step 3.4:

```bash
rocker --x11 --devices /dev/dxg --volume /usr/lib/wsl:/usr/lib/wsl:ro --env LD_LIBRARY_PATH=/usr/lib/wsl/lib GALLIUM_DRIVER=d3d12 --name osr osr-rover-sim
```

Here's what the extra parts do:

- `--devices /dev/dxg` passes the graphics chip into the container.
- `--volume /usr/lib/wsl:...` shares the Windows graphics driver files with the container.
- `--env ... GALLIUM_DRIVER=d3d12` tells the container's graphics software to draw through
  Windows (Direct3D 12).

> [!IMPORTANT]
> Copy it exactly, and keep `--name osr osr-rover-sim` at the **end**. If `osr-rover-sim` comes
> right after `--env` or `--volume`, rocker thinks the image name is another setting, and the command fails.

**If your laptop has two graphics chips** (for example Intel *and* NVIDIA), it may pick the
weaker one. To choose the NVIDIA one, add `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` after
`GALLIUM_DRIVER=d3d12`. Use `AMD` or `Intel` in place of `NVIDIA` to pick one of those.

#### Step 4: Check that the graphics chip is being used

Inside the container, install a small checking tool and run it:

```bash
sudo apt-get update && sudo apt-get install -y mesa-utils
glxinfo -B | grep -E "renderer|Accelerated"
```

| If the renderer says… | It means… |
| --- | --- |
| `D3D12 (NVIDIA GeForce ...)`, `D3D12 (Intel(R) Iris(R) Xe ...)`, or `D3D12 (AMD Radeon ...)` | ✅ It worked! Launch Gazebo as in step 3.4. |
| `llvmpipe` | ❌ It's still using the CPU. Redo Steps 1–3. |
| Nothing happens and the command never finishes | ❌ Your graphics chip doesn't work with WSL. See below. |

`mesa-utils` disappears when you exit the container, but you only need it for this one check.

**If it freezes:** close the window. In **PowerShell**, run `wsl --shutdown`, then reopen
Ubuntu and use the normal command from step 3.4. The simulation still works the CPU way.

> [!NOTE]
> **Why isn't there an NVIDIA-only setup?** In WSL, 3D graphics programs like Gazebo reach
> **every** brand of graphics chip through Direct3D 12, so the command above works for NVIDIA,
> Intel, and AMD alike. NVIDIA's extra container tools (`--nvidia runtime`, from the main
> README) give the container CUDA, a tool for machine learning, not 3D graphics. The simulation
> doesn't need them.


---

### 3.6 Every time after the first time

You only do Part 1 and steps 3.1–3.3 once. Next time, just open Ubuntu and run:

```bash
rocker --x11 --name osr osr-rover-sim
ros2 launch osr_gazebo empty_world.launch.py
```

(If your graphics chip worked in 3.5, use the longer `rocker` command from 3.5, Step 3
instead.)

And in a second Ubuntu window:

```bash
docker exec -it osr bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

To get the newest rover code and rebuild the image:

```bash
cd ~/osr-rover-code
git pull
docker build -t osr-rover-sim .
```


---

### 3.7 Simulation troubleshooting

**The simulation is slow or jumpy.**
With the normal command from step 3.4, that's expected. The CPU is drawing the 3D graphics, which is
slower. If your computer has a newer graphics chip, follow step 3.5. Otherwise, close other
programs to help.

**`Conflict. The container name "/osr" is already in use`.**
A container named `osr` is still running, maybe in another window. Either use that window, or
stop it with `docker rm -f osr` and try again.

**`docker exec` says `No such container: osr`.**
The first container isn't running. Start it with the `rocker` command first, and leave that
window open.

**No Gazebo window appears.**
- Make sure you used `--x11` in the `rocker` command.
- In PowerShell, run `wsl --update`, then `wsl --shutdown`, and reopen Ubuntu.

**Everything is stuck and nothing closes.**
In PowerShell, run `wsl --shutdown`. This restarts all of Linux, like turning it off and on
again. Then reopen Ubuntu and start over from step 3.4.

**`ros2: command not found`.**
You're in a plain Ubuntu window, not inside the container. Run the `rocker` command (or
`docker exec -it osr bash`) first.

---

## Want to learn more?

- [Main README](README.md): an overview of the rover code.
- [Simulation README](ROS/osr_gazebo/README.md): how the simulation works.
- [ROS overview](ROS/README.md): how the rover's software is organized.
- [Customized parts](https://github.com/Team-Turtlebots/open-source-rover/blob/master/parts_list/customized_parts.md):
  our changes to the official build.
- [Camera guide](TTB-Camera.md): set up the Arducam OV5647 camera on the rover's Pi 5.
- [Ryobi 18V battery configuration](setup/ryobi_18v_battery.md): if the real rover runs on
  a Ryobi ONE+ 18V battery, change the Roboclaw settings and
  `ROS/osr_bringup/config/roboclaw_params.yaml` as this page shows.
