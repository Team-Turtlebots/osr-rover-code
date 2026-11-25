import os
from glob import glob
from setuptools import setup

package_name = 'osr_biodiversity'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Team TurtleBots',
    maintainer_email='todo@example.com',
    description='Marpy biodiversity tools: phone live view, plant ID and observation log',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'web_node = osr_biodiversity.web_node:main',
        ],
    },
)
