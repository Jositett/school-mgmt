import cv2

print('Available camera backends:')
backends = [name for name in dir(cv2) if name.startswith('CAP_') and not name.startswith('CAP_PROP_')]
print(backends)

print('\nTesting different camera indices...')
for i in range(3):
    cap = cv2.VideoCapture(i)
    print(f'Camera {i}: opened={cap.isOpened()}')
    if cap.isOpened():
        print(f'  Backend: {cap.getBackendName()}')
        print(f'  Frame size: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}')
    cap.release()

print('\nTesting different backends for camera 0...')
backends_to_test = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW]
for backend in backends_to_test:
    try:
        cap = cv2.VideoCapture(0, backend)
        backend_name = cap.getBackendName()
        opened = cap.isOpened()
        print(f'Backend {backend_name}: opened={opened}')
        if opened:
            ret, frame = cap.read()
            print(f'  Can read frame: {ret}')
            if ret:
                print(f'  Frame shape: {frame.shape}')
        cap.release()
    except Exception as e:
        print(f'Backend {backend}: error - {e}')