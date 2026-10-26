# TurtleBots Guide: Run the Rover Simulation on Your Windows Computer

This guide walks you through running the Open Source Rover **simulation** on a Windows computer,
step by step. In the simulation, a 3D model of the rover drives around on your screen. You don't
need the real rover.

You don't need to know anything about Linux, WSL, Docker, or ROS before you start. Plan for about
**1–2 hours** the first time. Most of that is waiting for downloads.

> [!TIP]
> Each box with a gray background is a **command**. Copy it, paste it into the window the step
> names, and press **Enter**. Wait until the command finishes before running the next one.

---

## What are all these things?

| Name | What it is, in one sentence |
| --- | --- |
| **WSL** (Windows Subsystem for Linux) | Lets you run Linux, a different operating system, inside Windows. |
| **Ubuntu** | The version of Linux we install inside WSL. |
| **Terminal** | A window where you type commands instead of clicking buttons. |
| **Docker** | A tool that runs a "container": a sealed box with all the software the simulation needs already installed. |
| **Image** | The recipe-plus-ingredients for a container. We build it once and reuse it. |
| **rocker** | A helper that starts a Docker container and lets it open windows on your screen. |
| **ROS 2** | The robot software the real rover runs. The simulation uses the same code. |
| **Gazebo** | The 3D simulator that shows the rover and its physics. |

Here's how they fit together:

```
Windows  ─▶  WSL + Ubuntu  ─▶  Docker container  ─▶  ROS 2 + Gazebo  ─▶  rover on your screen
```

---

## Before you start

You need:

- A Windows 10 (version 22H2) or Windows 11 computer.
- An administrator password for that computer (ask a parent or teacher if you don't have one).
- About **15 GB of free disk space**.
- A good internet connection.

---

## Part 1: Install WSL and Ubuntu

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

## Part 2: Install Docker

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

### Check that Docker works

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

## Part 3: Get the rover code

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

## Part 4: Build the simulation image

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

## Part 5: Install rocker

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

## Part 6: Start the simulation 🚀

### 1. Start the container

In the Ubuntu terminal, run:

```bash
rocker --x11 --name osr osr-rover-sim
```

After a few seconds, the prompt changes, for example to `root@...:~/osr_ws#`. **You're now
inside the container.** ROS 2 is already set up there.

> [!NOTE]
> - The `--x11` part lets the container open windows on your screen.
> - Ignore the `xauth: file ... does not exist` messages if you skipped step 4 of Part 5. They're
>   harmless.
> - This command draws the 3D graphics with your computer's main processor (CPU), which works
>   on every computer but can be slow. If your computer has a newer graphics chip, Part 7 shows
>   how to use it instead.
> - Don't add `--nvidia runtime`, even if you have an NVIDIA card. It fails without extra
>   setup and doesn't make Gazebo faster. Part 7 explains what to do instead.

### 2. Launch Gazebo with the rover

Inside the container, run:

```bash
ros2 launch osr_gazebo empty_world.launch.py
```

A **Gazebo** window opens with the rover in an empty world. The first launch can take a minute.
If you see a warning that Gazebo Classic has reached "end of life", ignore it. The simulation
still works.

Leave this terminal running. If you close it, the simulation stops.

### 3. Drive the rover with your keyboard

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

### 4. Stop everything

- Press **Ctrl + C** in each terminal to stop the program running there.
- Type `exit` in the **first** terminal (the one where you ran `rocker`) to leave the container.

> [!WARNING]
> The container is **deleted** when you exit it. Any files you change inside the container are
> lost. That's fine for running the simulation, because the next `rocker` command starts a fresh
> one. To make a lasting change to the code, edit the files in `~/osr-rover-code` (outside the
> container), then rebuild the image (Part 4).

---

## Part 7 (optional): Use your graphics chip to make it faster ⚡

By default, the simulation draws its 3D graphics with the CPU. A graphics chip (GPU) is
built for exactly this job, so using one makes Gazebo much smoother. WSL can share your Windows
graphics chip with Linux, and Docker can pass it into the container.

### Does my computer qualify?

| Your graphics | Good to try? |
| --- | --- |
| **NVIDIA** GeForce or RTX card (GTX 900 series or newer) | ✅ Yes |
| **Intel** Iris Xe or Arc (11th-gen Intel Core or newer) | ✅ Yes |
| **AMD** Radeon graphics in a Ryzen 5000-series or newer processor, or a Radeon RX card | ✅ Yes |
| Older **Intel UHD / HD Graphics** | ❌ Skip Part 7. We tested one and the simulation froze. |

To find out what you have: press **Ctrl + Shift + Esc** to open Task Manager, click
**Performance**, and look at the entries named **GPU 0** (and **GPU 1**, if there is one). The
name of the graphics chip is in the top-right corner.

Using **Windows 11** gives the best chance of this working.

### Step 1: Update your graphics driver in Windows

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

### Step 2: Check that Ubuntu can see the graphics chip

Open Ubuntu and run:

```bash
ls /dev/dxg
```

It should print `/dev/dxg`. If it says `No such file or directory`, WSL can't reach your graphics
chip. Redo Step 1, and check that you're on Windows 10 22H2 or Windows 11.

With an **NVIDIA** card, also run `nvidia-smi`. It should print a table with your card's name.

### Step 3: Start the container with the graphics chip

Use this longer command instead of the one in Part 6:

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

### Step 4: Check that the graphics chip is being used

Inside the container, install a small checking tool and run it:

```bash
sudo apt-get update && sudo apt-get install -y mesa-utils
glxinfo -B | grep -E "renderer|Accelerated"
```

| If the renderer says… | It means… |
| --- | --- |
| `D3D12 (NVIDIA GeForce ...)`, `D3D12 (Intel(R) Iris(R) Xe ...)`, or `D3D12 (AMD Radeon ...)` | ✅ It worked! Launch Gazebo as in Part 6. |
| `llvmpipe` | ❌ It's still using the CPU. Redo Steps 1–3. |
| Nothing happens and the command never finishes | ❌ Your graphics chip doesn't work with WSL. See below. |

`mesa-utils` disappears when you exit the container, but you only need it for this one check.

**If it freezes:** close the window. In **PowerShell**, run `wsl --shutdown`, then reopen
Ubuntu and use the normal command from Part 6. The simulation still works the CPU way.

> [!NOTE]
> **Why isn't there an NVIDIA-only setup?** In WSL, 3D graphics programs like Gazebo reach
> **every** brand of graphics chip through Direct3D 12, so the command above works for NVIDIA,
> Intel, and AMD alike. NVIDIA's extra container tools (`--nvidia runtime`, from the main
> README) give the container CUDA, a tool for machine learning, not 3D graphics. The simulation
> doesn't need them.

---

## Every time after the first time

You only do Parts 1–5 once. Next time, just open Ubuntu and run:

```bash
rocker --x11 --name osr osr-rover-sim
ros2 launch osr_gazebo empty_world.launch.py
```

(If your graphics chip worked in Part 7, use the longer `rocker` command from Part 7, Step 3
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

## Troubleshooting

**The simulation is slow or jumpy.**
With the normal command from Part 6, that's expected. The CPU is drawing the 3D graphics, which is
slower. If your computer has a newer graphics chip, follow Part 7. Otherwise, close other
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
again. Then reopen Ubuntu and start over from Part 6.

**`ros2: command not found`.**
You're in a plain Ubuntu window, not inside the container. Run the `rocker` command (or
`docker exec -it osr bash`) first.

---

## Want to learn more?

- [Main README](README.md): an overview of the rover code.
- [Simulation README](ROS/osr_gazebo/README.md): how the simulation works.
- [ROS overview](ROS/README.md): how the rover's software is organized.
