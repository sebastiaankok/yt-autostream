{
  description = "YouTube autostream environment";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};

  in {
    devShells.${system}.default = pkgs.mkShell {
      buildInputs = [
        pkgs.python311
        pkgs.python311Packages.yt-dlp
        pkgs.python311Packages.ffmpeg-python
        pkgs.python311Packages.datetime
        pkgs.ffmpeg-full
        pkgs.intel-media-driver
        pkgs.libva
        pkgs.libva-utils
        pkgs.libvdpau-va-gl
        pkgs.vaapiIntel
        pkgs.vaapiVdpau
        pkgs.screen
      ];

      shellHook = ''
        export LIBVA_DRIVER_NAME=iHD
        export LIBVA_DRIVERS_PATH=${pkgs.intel-media-driver}/lib/dri
        export VDPAU_DRIVER_PATH=${pkgs.intel-media-driver}/lib/vdpau
        export DISPLAY=:0
      '';
    };
  };
}
