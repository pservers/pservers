prefix=/usr

all:

clean:
	fixme

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/sbin"
	install -m 0755 pservers "$(DESTDIR)/$(prefix)/sbin"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/pservers"
	cp -r lib/* "$(DESTDIR)/$(prefix)/lib/pservers"
	find "$(DESTDIR)/$(prefix)/lib/pservers" -type f -maxdepth 1 | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/lib/pservers" -type d -maxdepth 1 | xargs chmod 755

	install -d -m 0755 "$(DESTDIR)/etc/pservers"

	install -d -m 0755 "$(DESTDIR)/lib/systemd/system"
	install -m 0644 data/pservers.service "$(DESTDIR)/lib/systemd/system"

	find "$(DESTDIR)/$(prefix)/lib64/pservers/plugins.d/$(plugin)" -name "*.py" | xargs chmod 755		# FIXME

uninstall:
	rm -f "$(DESTDIR)/lib/systemd/system/pservers.service"
	rm -rf "$(DESTDIR)/$(prefix)/lib/pservers"
	rm -f "$(DESTDIR)/$(prefix)/sbin/pservers"

.PHONY: all clean install uninstall
