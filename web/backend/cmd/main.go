// Tasmia web backend entry point: the front door.
// Loads the shared config, builds the App and listens. All logic
// lives in the library package.
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"backend"
)

func main() {
	config, err := backend.LoadConfig("")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	app, err := backend.New(&config)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	addr := fmt.Sprintf("%s:%d", config.WebApp.Host, config.WebApp.Port)
	fmt.Printf("Tasmia web on %s\n", addr)
	log.Fatal(http.ListenAndServe(addr, app))
}
