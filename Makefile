prefix=/usr

all:

clean:
	fixme

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/sbin"
	install -m 0755 pservers "$(DESTDIR)/$(prefix)/sbin"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib64/pservers"
	cp -r lib/* "$(DESTDIR)/$(prefix)/lib64/pservers"
	find "$(DESTDIR)/$(prefix)/lib64/pservers" -type f -maxdepth 1 | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/lib64/pservers" -type d -maxdepth 1 | xargs chmod 755

	install -d -m 0755 "$(DESTDIR)/etc/pservers"

	install -d -m 0755 "$(DESTDIR)/lib/systemd/system"
	install -m 0644 data/pservers.service "$(DESTDIR)/lib/systemd/system"

uninstall:
	rm -f "$(DESTDIR)/lib/systemd/system/pservers.service"
	rm -rf "$(DESTDIR)/$(prefix)/lib64/pservers"
	rm -f "$(DESTDIR)/$(prefix)/sbin/pservers"

.PHONY: all clean install uninstall
