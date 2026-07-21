if [[ "$TEST" = "docs" || "$TEST" = "publish" ]]
then
  sudo apt-get update
  sudo apt-get install -y libgirepository1.0-dev libostree-dev
fi

# PyGObject must match the system GLib version, so exempt it from lowerbounds pinning
if [[ "$TEST" = "lowerbounds" ]]; then
  sed -i '/PyGObject/d' lowerbounds_constraints.txt
fi
