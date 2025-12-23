# Troubleshooting Boot Issues

## Common Boot Problems and Solutions

### System Won't Power On

**Symptoms:**
- No lights, no fans, complete silence
- Power button does nothing

**Solutions:**

1. **Check Power Connections**
   - Verify power cable is plugged into wall outlet and PSU
   - Check that PSU power switch is in the ON position (I, not O)
   - Try a different power cable
   - Test the wall outlet with another device

2. **Check Internal Power Connections**
   - Open case and verify 24-pin motherboard power connector is fully seated
   - Check 8-pin (or 4+4 pin) CPU power connector
   - Reseat all power connections

3. **Test Power Supply**
   - Try the paperclip test (short PS_ON to ground on 24-pin connector)
   - If PSU fan doesn't spin, PSU may be faulty
   - Contact support for PSU replacement under warranty

---

### System Powers On But No Display

**Symptoms:**
- Fans spin, lights turn on
- Monitor shows "No Signal"
- No POST beep or error beeps

**Solutions:**

1. **Check Monitor and Cables**
   - Verify monitor is powered on and set to correct input
   - Try a different video cable (HDMI, DisplayPort, etc.)
   - Test with a different monitor if available
   - **IMPORTANT:** Ensure cable is plugged into GPU, NOT motherboard (if you have a dedicated graphics card)

2. **Reseat Graphics Card**
   - Power off and unplug system
   - Remove GPU and reseat firmly in PCIe slot
   - Ensure PCIe power cables are connected to GPU
   - Check that GPU retention clip is engaged

3. **Try Integrated Graphics** (if available)
   - Remove dedicated GPU
   - Connect monitor to motherboard video output
   - If display works, GPU or PCIe slot may be faulty

4. **Reseat RAM**
   - Remove all RAM sticks
   - Install one stick in the primary slot (usually DIMM A2)
   - If no display, try a different stick
   - If one stick works, test others individually

5. **Clear CMOS**
   - Locate CMOS battery on motherboard
   - Remove battery for 30 seconds
   - Reinsert battery and try booting
   - Alternative: Use CMOS clear jumper (consult motherboard manual)

---

### POST Beep Codes

**Understanding Beep Patterns:**

Different motherboard manufacturers use different beep codes. Common patterns:

**1 short beep:** Normal POST, system OK
**2 short beeps:** POST error, check screen for error code
**3 short beeps:** Memory error (reseat or replace RAM)
**1 long, 2 short beeps:** Video card error
**1 long, 3 short beeps:** Video card error
**Continuous beeping:** Memory or power issue

**No beep at all:**
- Motherboard may not have a speaker
- CPU, motherboard, or power issue

---

### System Boots to BIOS But Won't Load Windows

**Symptoms:**
- BIOS/UEFI loads normally
- Windows logo doesn't appear or system hangs

**Solutions:**

1. **Check Boot Order**
   - Enter BIOS (usually Del, F2, or F12 during startup)
   - Verify boot drive is set as first boot device
   - Disable unused boot options

2. **Check Drive Detection**
   - In BIOS, verify that your OS drive is detected
   - If not detected, check SATA/NVMe connections
   - Try a different SATA port or M.2 slot

3. **Windows Boot Repair**
   - Create Windows installation USB
   - Boot from USB
   - Select "Repair your computer"
   - Use Startup Repair tool

4. **Check for Drive Failure**
   - Boot into BIOS and run drive diagnostics (if available)
   - Listen for clicking sounds from HDD (sign of failure)
   - Contact support if drive appears to be failing

---

### System Crashes or Freezes During Boot

**Symptoms:**
- System starts to boot but freezes or crashes
- Blue screen of death (BSOD)
- Automatic restart loop

**Solutions:**

1. **Boot into Safe Mode**
   - Restart and press F8 repeatedly (or Shift+F8)
   - Select "Safe Mode"
   - If successful, issue is likely software/driver related

2. **Check Temperatures**
   - Enter BIOS and check CPU temperature
   - Should be under 50°C at idle
   - If overheating, check that CPU cooler is properly mounted

3. **Test RAM**
   - Boot from Windows installation USB
   - Run Windows Memory Diagnostic
   - Or download and run MemTest86

4. **Update or Roll Back Drivers**
   - In Safe Mode, use Device Manager
   - Update or roll back recently changed drivers
   - Especially graphics and chipset drivers

5. **Check for Loose Components**
   - Reseat all components (GPU, RAM, storage)
   - Check all power and data cables

---

### Specific Error Messages

**"No Bootable Device" or "Boot Device Not Found"**
- Boot drive not detected
- Check SATA/NVMe connections
- Verify boot order in BIOS
- Drive may have failed

**"CMOS Checksum Error"**
- CMOS battery may be dead
- Replace CR2032 battery on motherboard
- Clear CMOS and reconfigure BIOS settings

**"CPU Fan Error"**
- CPU fan not detected or running too slow
- Check fan connection to CPU_FAN header
- Verify fan is spinning
- Adjust fan curve in BIOS or disable warning (not recommended)

**"Overclocking Failed"**
- System unstable with current overclock settings
- BIOS will usually load default settings automatically
- Reduce overclock or increase voltage slightly

---

## Advanced Troubleshooting

### Breadboarding (Testing Outside Case)

If system won't POST:
1. Remove motherboard from case
2. Place on non-conductive surface (motherboard box)
3. Install only essential components:
   - CPU and cooler
   - One stick of RAM
   - Power supply
   - Monitor (connected to motherboard or GPU)
4. Short power button pins with screwdriver
5. If system POSTs, issue may be case standoff short

---

### Testing with Minimal Hardware

Remove all non-essential components:
- Extra RAM sticks (keep one)
- Dedicated GPU (use integrated if available)
- All storage drives except OS drive
- All USB devices
- All expansion cards

If system boots, add components back one at a time to identify culprit.

---

### BIOS/UEFI Settings to Check

**Boot Issues:**
- **Secure Boot:** Try disabling
- **Fast Boot:** Try disabling
- **CSM/Legacy Boot:** Enable if using older OS
- **SATA Mode:** Try switching between AHCI and RAID

**Stability Issues:**
- **XMP/EXPO:** Disable RAM overclock profile
- **CPU Overclock:** Reset to default
- **Load Optimized Defaults:** Reset all BIOS settings

---

## When to Contact Support

Contact SmartSupport if:
- You've tried all troubleshooting steps
- You suspect hardware failure
- You're uncomfortable opening the case
- System is under warranty

**What to Have Ready:**
- Order number or serial number
- Description of the problem
- Troubleshooting steps already attempted
- Any error messages or beep codes

**Support Contact:**
- Phone: 1-800-SUPPORT (24/7)
- Email: support@smartsupport.com
- Live Chat: www.smartsupport.com/support

---

## Preventive Measures

**To Avoid Boot Issues:**
- Keep BIOS/UEFI updated
- Use surge protector or UPS
- Ensure adequate cooling
- Keep system clean (dust-free)
- Don't force components during installation
- Handle components by edges, avoid touching contacts
- Use anti-static precautions

---

## Warranty Coverage

Boot issues caused by hardware failure are covered under warranty:
- Faulty motherboard, CPU, RAM, PSU, or storage
- Manufacturing defects
- Component failures during normal use

**Not Covered:**
- Physical damage from mishandling
- Damage from power surges (without surge protector)
- Issues caused by user modifications
- Software problems (unless part of support plan)

**RMA Process:**
1. Contact support for diagnosis
2. Receive RMA number
3. Ship system or component (prepaid label provided)
4. Repair or replacement within 5-7 business days
5. Free return shipping

---

For immediate assistance with boot issues, contact our 24/7 support team at 1-800-SUPPORT.
