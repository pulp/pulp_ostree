if [[ "$TEST" = "docs" || "$TEST" = "publish" ]]
then
  sudo apt-get install -y libgirepository1.0-dev libostree-dev
fi
