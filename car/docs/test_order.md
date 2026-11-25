# Test order - No OLED / No RGB Version

1. Arduino only, motor battery disconnected: Serial Monitor shows `SMART_CAR_R4_NO_DISPLAY_READY`.
2. Test HC-SR04 / IR / GY-87 telemetry through Serial Monitor.
3. Test active buzzer with `ALARM 5`.
4. Kê xe lên, connect motor battery, send `UNLOCK`, `D 80 80`, `S`.
5. If one side reversed, edit `LEFT_INVERT` or `RIGHT_INVERT`.
6. If one wheel within same side reversed, swap that motor's two wires.
7. Run Raspberry Pi server.
8. Open web from laptop.
9. Start laptop camera, register face, verify face.
10. Test web control.
11. Test failed face 3 times -> buzzer + saved image + history.
12. Test emergency button -> motor stops immediately.
13. Test voice control.
14. Test AI lane with green tape.
15. Test auto park with marker ID 7.
