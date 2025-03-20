import numpy as np
import matplotlib.pyplot as plt
from ipywidgets import interact, FloatSlider, IntSlider

def pseudo_voigt(xx, yy, x0, y0, amplitude, sigma, gamma, eta):
    """
    Generate a pseudo Voigt profile.
    
    - Gaussian part: exp(-((x-x0)^2+(y-y0)^2) / (2*sigma^2))
    - Lorentzian part: 1 / (1 + ((x-x0)^2+(y-y0)^2)/gamma^2)
    - eta: mixing factor (0 gives pure Gaussian, 1 gives pure Lorentzian)
    """
    # Compute squared distance from the center
    r2 = (xx - x0)**2 + (yy - y0)**2
    gaussian = np.exp(-r2 / (2 * sigma**2))
    lorentzian = 1 / (1 + r2 / gamma**2)
    return amplitude * (eta * lorentzian + (1 - eta) * gaussian)

def simulate_image(nx, ny, amplitude, sigma, gamma, eta, background, poisson_level, read_noise_std):
    # Create coordinate grids
    x = np.arange(nx)
    y = np.arange(ny)
    xx, yy = np.meshgrid(x, y)
    
    # Define center (using pixel center convention)
    x0, y0 = nx / 2, ny / 2
    
    # Create direct beam profile using pseudo Voigt
    beam = pseudo_voigt(xx, yy, x0, y0, amplitude, sigma, gamma, eta)
    
    # Simulate background noise:
    # Poisson noise (shot noise) on a constant background
    noise_poisson = np.random.poisson(poisson_level, size=(ny, nx))
    
    # Gaussian read noise (electronic noise)
    noise_read = np.random.normal(loc=0, scale=read_noise_std, size=(ny, nx))
    
    # Sum up beam, background, and noise
    image = beam + background + noise_poisson + noise_read
    
    # Clip negative values (if any)
    image[image < 0] = 0
    return image

def plot_image(amplitude=1000, sigma=10, gamma=10, eta=0.5, background=10, poisson_level=10, read_noise_std=5):
    nx, ny = 1024, 1024  # detector dimensions
    img = simulate_image(nx, ny, amplitude, sigma, gamma, eta, background, poisson_level, read_noise_std)
    
    plt.figure(figsize=(8, 8))
    plt.imshow(img, cmap='gray', origin='lower')
    plt.colorbar(label='Intensity')
    plt.title("Simulated Electron Diffraction: Direct Beam (Pseudo Voigt) with Noise")
    plt.xlabel("Pixel (fs)")
    plt.ylabel("Pixel (ss)")
    plt.show()

# Create interactive sliders to adjust parameters in real time
interact(
    plot_image,
    amplitude=IntSlider(value=1000, min=0, max=5000, step=100, description='Amplitude'),
    sigma=FloatSlider(value=10, min=1, max=50, step=0.5, description='Sigma (Gaussian)'),
    gamma=FloatSlider(value=10, min=1, max=50, step=0.5, description='Gamma (Lorentzian)'),
    eta=FloatSlider(value=0.5, min=0, max=1, step=0.01, description='Eta (Mixing)'),
    background=IntSlider(value=10, min=0, max=100, step=1, description='Background'),
    poisson_level=IntSlider(value=10, min=0, max=100, step=1, description='Poisson Level'),
    read_noise_std=IntSlider(value=5, min=0, max=20, step=1, description='Read Noise Std')
)
