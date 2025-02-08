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
        pkgs.libva-utils
        pkgs.screen
      ];

      shellHook = ''
        export LIBVA_DRIVER_NAME=iHD
        export LIBVA_DRIVERS_PATH=${pkgs.intel-media-driver}/lib/dri
        export VDPAU_DRIVER_PATH=${pkgs.intel-media-driver}/lib/vdpau
        export DISPLAY=:0
        export MKL_NUM_THREADS=20
        export OPENBLAS_NUM_THREADS=20
        export VECLIB_MAXIMUM_THREADS=20
        export NUMEXPR_NUM_THREADS=20
        export FFMPEG_THREADS=16  # Leave 4 threads for system
      '';
    };
  };
}
